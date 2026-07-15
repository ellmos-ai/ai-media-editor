"""Compute-Routing fuer die Transkription: Mac Studio primaer, lokal Fallback.

Die schwere STT-Last (faster-whisper / WhisperX + torch) laeuft bevorzugt auf
dem 24/7-Mac Studio (mehr RAM/GPU, WhisperX dort sauber installierbar). Der
Laptop schickt die Eingabedatei hin und holt das fertige Scribe-JSON zurueck.
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

import re
import shlex
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

try:
    from . import transcribe_local
except ImportError:  # standalone import from stt/
    import transcribe_local

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
    user = str(cfg["user"])
    host = str(cfg["host"])
    if not re.fullmatch(r"[A-Za-z0-9._-]+", user) or user.startswith("-"):
        raise ValueError("Ungültiger SSH-Benutzername in settings.json")
    if not re.fullmatch(r"[A-Za-z0-9._:\[\]-]+", host) or host.startswith("-"):
        raise ValueError("Ungültiger SSH-Host in settings.json")
    return f"{user}@{host}"


def _remote_spec(cfg: dict, path: str) -> str:
    """Build an scp remote spec whose path remains one shell argument."""
    return f"{_target(cfg)}:{shq(path)}"


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
    try:
        r = subprocess.run(
            _ssh_base(cfg) + [_target(cfg), remote_cmd],
            capture_output=True, text=True, timeout=timeout,
        )
        return r.returncode, r.stdout, r.stderr
    except Exception as exc:
        return -1, "", str(exc)


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

    workdir = str(cfg["workdir"]).rstrip("/")
    if not workdir:
        if verbose:
            print("  [mac] workdir ist leer -> lokaler Fallback")
        return None
    stem = media.stem
    selected_model = model or ("large-v3" if engine == "whisperx" else "medium")
    job_id = uuid.uuid4().hex
    remote_root = f"{workdir}/ai_media_{job_id}"
    remote_media = f"{remote_root}/{media.name}"
    remote_edit = f"{remote_root}/edit"
    remote_token = f"{remote_root}/hf_token.txt"
    local_dir = edit_dir / "transcripts"
    local_dir.mkdir(parents=True, exist_ok=True)
    local_json = local_dir / f"{stem}.json"
    local_meta = local_json.with_suffix(".meta")
    json_tmp = local_dir / f".{stem}.{job_id}.json.tmp"
    meta_tmp = local_dir / f".{stem}.{job_id}.meta.tmp"

    try:
        # 1. Isolated remote directory and helper scripts.
        rc, _, err = _ssh_run(
            cfg,
            f"umask 077; mkdir -p {shq(remote_root)} && chmod 700 {shq(remote_root)}",
        )
        if rc != 0:
            if verbose:
                print(f"  [mac] mkdir fehlgeschlagen: {err.strip()[:200]}")
            return None
        for fname in ("transcribe_local.py", "scribe_schema.py"):
            if not _scp(cfg, str(HERE / fname), _remote_spec(cfg, f"{remote_root}/{fname}")):
                if verbose:
                    print(f"  [mac] Upload {fname} fehlgeschlagen -> lokaler Fallback")
                return None

        # 2. Upload the complete input media. Remote paths are shell-quoted.
        if verbose:
            print(f"  [mac] lade {media.name} hoch ...", flush=True)
        if not _scp(cfg, str(media), _remote_spec(cfg, remote_media)):
            if verbose:
                print("  [mac] Medien-Upload fehlgeschlagen -> lokaler Fallback")
            return None
        rc, _, err = _ssh_run(cfg, f"chmod 600 {shq(remote_media)}", timeout=60)
        if rc != 0:
            if verbose:
                print(f"  [mac] Medien-Dateirechte fehlgeschlagen: {err.strip()[:200]}")
            return None

        # 3. Use a temporary token file so secrets do not appear in process arguments.
        with tempfile.TemporaryDirectory(prefix="ai-media-editor-token-") as secret_dir:
            if hf_token:
                token_path = Path(secret_dir) / "hf_token.txt"
                token_path.write_text(hf_token, encoding="utf-8")
                if not _scp(cfg, str(token_path), _remote_spec(cfg, remote_token)):
                    if verbose:
                        print("  [mac] Token-Upload fehlgeschlagen -> lokaler Fallback")
                    return None
                rc, _, err = _ssh_run(cfg, f"chmod 600 {shq(remote_token)}", timeout=60)
                if rc != 0:
                    if verbose:
                        print(f"  [mac] Token-Dateirechte fehlgeschlagen: {err.strip()[:200]}")
                    return None

            parts = [
                str(cfg["venv_activate"]), "&&",
                "python", shq(f"{remote_root}/transcribe_local.py"), shq(remote_media),
                "--edit-dir", shq(remote_edit),
                "--engine", shq(engine),
                "--language", shq(language),
                "--device", "auto",
                "--model", shq(selected_model),
            ]
            if num_speakers:
                parts += ["--num-speakers", str(num_speakers)]
            if hf_token:
                parts += ["--hf-token-file", shq(remote_token)]
            remote_cmd = " ".join(parts)

            if verbose:
                print(f"  [mac] transkribiere ({engine}) ...", flush=True)
            rc, _, err = _ssh_run(cfg, remote_cmd, timeout=7200)
            if rc != 0:
                if verbose:
                    print(f"  [mac] Transkription fehlgeschlagen -> lokaler Fallback\n    {err.strip()[-300:]}")
                return None

        # 4. Download to temporary files and validate before replacing a good cache.
        remote_json = _remote_spec(cfg, f"{remote_edit}/transcripts/{stem}.json")
        remote_meta = _remote_spec(cfg, f"{remote_edit}/transcripts/{stem}.meta")
        if not _scp(cfg, remote_json, str(json_tmp)) or not _scp(cfg, remote_meta, str(meta_tmp)):
            if verbose:
                print("  [mac] Download Ergebnis fehlgeschlagen -> lokaler Fallback")
            return None
        if not transcribe_local.cache_is_valid(
            media, json_tmp, engine, selected_model, language, "auto",
            num_speakers, hf_token, meta_tmp,
        ):
            if verbose:
                print("  [mac] Ergebnis-/Cachevalidierung fehlgeschlagen -> lokaler Fallback")
            return None
        os.replace(json_tmp, local_json)
        os.replace(meta_tmp, local_meta)

        if verbose:
            print(f"  [mac] fertig -> {local_json.name}")
        return local_json
    finally:
        json_tmp.unlink(missing_ok=True)
        meta_tmp.unlink(missing_ok=True)
        _ssh_run(cfg, f"rm -rf {shq(remote_root)}", timeout=60)


def shq(s: str) -> str:
    """Quote one POSIX-shell argument while preserving a leading home shortcut."""
    value = str(s)
    if value == "~":
        return '"$HOME"'
    if value.startswith("~/"):
        return '"$HOME"/' + shlex.quote(value[2:])
    return shlex.quote(value)
