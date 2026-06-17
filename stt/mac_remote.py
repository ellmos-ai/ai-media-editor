"""Compute-Routing fuer die Transkription: Mac Studio primaer, lokal Fallback.

Die schwere STT-Last (faster-whisper / WhisperX + torch) laeuft bevorzugt auf
dem 24/7-Mac Studio (mehr RAM/GPU, WhisperX dort sauber installierbar). Der
Laptop schickt nur das Audio hin und holt das fertige Scribe-JSON zurueck.
Faellt SSH aus, transkribiert der Aufrufer lokal weiter.

Transportweg (alles ueber den vorhandenen SSH-Key, kein Passwort):
  1. Erreichbarkeit pruefen (ssh echo, kurzer Timeout)
  2. transcribe_local.py + scribe_schema.py auf den Mac spiegeln
  3. Medien-Datei per scp hochladen
  4. Remote transkribieren (im science-venv)
  5. transcripts/<stem>.json zuruecksaugen
  6. Remote-Arbeitsdateien aufraeumen

run_remote() gibt den lokalen Ziel-JSON-Pfad zurueck — oder None, wenn der
Mac nicht erreichbar/der Lauf fehlgeschlagen ist (Signal fuer Fallback).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _ssh_base(cfg: dict) -> list[str]:
    key = cfg["ssh_key"]
    return [
        "ssh", "-i", key,
        "-o", f"ConnectTimeout={cfg.get('connect_timeout', 12)}",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=accept-new",
    ]


def _target(cfg: dict) -> str:
    return f"{cfg['user']}@{cfg['host']}"


def is_reachable(cfg: dict) -> bool:
    try:
        r = subprocess.run(
            _ssh_base(cfg) + [_target(cfg), "echo MAC_OK"],
            capture_output=True, text=True, timeout=cfg.get("connect_timeout", 12) + 5,
        )
        return r.returncode == 0 and "MAC_OK" in r.stdout
    except Exception:
        return False


def _scp(cfg: dict, src: str, dst: str) -> bool:
    try:
        r = subprocess.run(
            ["scp", "-i", cfg["ssh_key"],
             "-o", f"ConnectTimeout={cfg.get('connect_timeout', 12)}",
             "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new",
             src, dst],
            capture_output=True, text=True, timeout=1800,
        )
        return r.returncode == 0
    except Exception:
        return False


def _ssh_run(cfg: dict, remote_cmd: str, timeout: int = 3600) -> tuple[int, str, str]:
    r = subprocess.run(
        _ssh_base(cfg) + [_target(cfg), remote_cmd],
        capture_output=True, text=True, timeout=timeout,
    )
    return r.returncode, r.stdout, r.stderr


def run_remote(
    media: Path,
    edit_dir: Path,
    cfg: dict,
    engine: str = "faster",
    model: str | None = None,
    language: str = "de",
    num_speakers: int | None = None,
    hf_token: str | None = None,
    verbose: bool = True,
) -> Path | None:
    """Transkribiert media auf dem Mac. Gibt lokalen JSON-Pfad zurueck oder None."""
    if not is_reachable(cfg):
        if verbose:
            print("  [mac] nicht erreichbar -> lokaler Fallback")
        return None

    target = _target(cfg)
    workdir = cfg["workdir"]
    stem = media.stem
    remote_media = f"{workdir}/{media.name}"
    remote_edit = f"{workdir}/edit_{stem}"

    # 1. Arbeitsverzeichnis + Script-Spiegel anlegen
    rc, _, err = _ssh_run(cfg, f"mkdir -p {workdir}")
    if rc != 0:
        if verbose:
            print(f"  [mac] mkdir fehlgeschlagen: {err.strip()[:200]}")
        return None
    for fname in ("transcribe_local.py", "scribe_schema.py"):
        if not _scp(cfg, str(HERE / fname), f"{target}:{workdir}/{fname}"):
            if verbose:
                print(f"  [mac] Upload {fname} fehlgeschlagen -> lokaler Fallback")
            return None

    # 2. Medien hochladen
    if verbose:
        print(f"  [mac] lade {media.name} hoch ...", flush=True)
    if not _scp(cfg, str(media), f"{target}:{remote_media}"):
        if verbose:
            print("  [mac] Medien-Upload fehlgeschlagen -> lokaler Fallback")
        return None

    # 3. Remote transkribieren
    parts = [
        cfg["venv_activate"], "&&",
        f"python {workdir}/transcribe_local.py", shq(remote_media),
        "--edit-dir", shq(remote_edit),
        "--engine", engine,
        "--language", language,
        "--device", "auto",
    ]
    if model:
        parts += ["--model", model]
    if num_speakers:
        parts += ["--num-speakers", str(num_speakers)]
    if hf_token:
        parts += ["--hf-token", hf_token]
    remote_cmd = " ".join(parts)

    if verbose:
        print(f"  [mac] transkribiere ({engine}) ...", flush=True)
    rc, out, err = _ssh_run(cfg, remote_cmd, timeout=7200)
    if rc != 0:
        if verbose:
            print(f"  [mac] Transkription fehlgeschlagen -> lokaler Fallback\n    {err.strip()[-300:]}")
        return None

    # 4. Ergebnis zuruecksaugen
    local_dir = edit_dir / "transcripts"
    local_dir.mkdir(parents=True, exist_ok=True)
    local_json = local_dir / f"{stem}.json"
    remote_json = f"{target}:{remote_edit}/transcripts/{stem}.json"
    if not _scp(cfg, remote_json, str(local_json)):
        if verbose:
            print("  [mac] Download Ergebnis fehlgeschlagen -> lokaler Fallback")
        return None

    # 5. Remote aufraeumen (best effort)
    _ssh_run(cfg, f"rm -rf {shq(remote_media)} {shq(remote_edit)}", timeout=60)

    if verbose:
        print(f"  [mac] fertig -> {local_json.name}")
    return local_json


def shq(s: str) -> str:
    """Minimales Shell-Quoting fuer Remote-Pfade (Tilde bleibt expandierbar)."""
    if s.startswith("~"):
        # Tilde nicht quoten, Rest schon
        return s
    return "'" + s.replace("'", "'\\''") + "'"
