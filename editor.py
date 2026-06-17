"""Podcast/Video-Editor — Usecase-Orchestrator.

Automatisiert die deterministischen Vorbereitungsschritte des
Claude-Code-Video-Editor-Workflows (nach dem Setup von Julian Ivanov,
aber mit lokalem/Mac-STT statt ElevenLabs):

    Medien -> [richtige Engine + Compute-Routing] -> Scribe-JSON
           -> pack_transcripts -> takes_packed.md
           -> Hinweis, wie es je Usecase weitergeht.

Die kreative Arbeit (Schnitt-Entscheidungen, Animationen, Render) faehrt
danach Claude Code interaktiv, geleitet durch CLAUDE.md / USECASES.md.

Die 7 Usecases (vom User definiert):

  1  Audio,    1 Sprecher       -> Audio-Podcast geschnitten
  2  Audio,    N Sprecher       -> Audio-Podcast geschnitten, Sprecher-getrennt
  3  Video A+V, 1 Sprecher      -> Video geschnitten + Animationen (Original-Setup)
  4  Video A+V, N Sprecher      -> Video geschnitten + Animationen, Sprecher-Tracking
  5  Video, nur Tonspur nutzen  -> Audio-Podcast (Bild verworfen)
  6  Erklaervideo aus Audio     -> voll generiertes Video (frontend-design + Hyperframes)
  7  Audio + animiertes Cover   -> Audio + Hyperframes-Cover-Loop

Usage:
    python editor.py prepare <media> --mode 3 [--project <name>] [--num-speakers N]
    python editor.py frames <video|projekt> [--every 10]      # Bild-Übersicht
    python editor.py frames <video|projekt> --from 30 --to 45 --step 0.25  # Zoom
    python editor.py modes        # Tabelle aller Usecases
    python editor.py doctor       # Umgebungs-Check (Mac, venv, ffmpeg, hyperframes)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "stt"))
sys.path.insert(0, str(HERE / "tools"))

import transcribe_local  # noqa: E402
import mac_remote  # noqa: E402
import diarize_llm  # noqa: E402
import frame_view  # noqa: E402

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}


# --------------------------------------------------------------------------- #
# Usecase-Definitionen
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Usecase:
    mode: int
    label: str
    input_kind: str        # "audio" | "video"
    multi_speaker: bool
    output_kind: str       # "audio_cut" | "video_cut" | "generated_video" | "audio_cover" | "ad_clip"
    engine: str            # "faster" | "whisperx"
    next_steps: str


USECASES: dict[int, Usecase] = {
    1: Usecase(1, "Audio, 1 Sprecher", "audio", False, "audio_cut", "faster",
               "Schnitt: takes_packed.md lesen -> Fueller/Pausen/Versprecher raus -> "
               "edl.json (audio-only) -> render.py --no-subtitles fuer reinen Audioschnitt."),
    2: Usecase(2, "Audio, mehrere Sprecher (Gespraech)", "audio", True, "audio_cut", "faster+llm-diar",
               "Sprecher tokenfrei per LLM zuordnen (diarize_llm, kein HF-Token), dann wie 1: "
               "S0/S1 im takes_packed.md beachten, Handoffs mit Luft (400-600ms)."),
    3: Usecase(3, "Video (A+V), 1 Sprecher", "video", False, "video_cut", "faster",
               "Voller video-use-Workflow: takes_packed.md -> edl.json -> Animationen via "
               "frontend-design + Hyperframes -> render.py (Subtitles LAST). Das Original-Setup."),
    4: Usecase(4, "Video (A+V), mehrere Sprecher", "video", True, "video_cut", "faster+llm-diar",
               "Wie 3 + Sprecher tokenfrei per LLM (diarize_llm) -> Lower-Thirds/Namens-Karten "
               "pro Sprecher (S0/S1...) moeglich. Kein HF-Token."),
    5: Usecase(5, "Video-Ausgangsmaterial, nur Tonspur", "video", False, "audio_cut", "faster",
               "Nur die Audiospur wird genutzt: extrahieren -> wie Usecase 1. Das Bild wird "
               "verworfen (Ergebnis ist ein Audio-Podcast). --num-speakers fuer Gespraech setzen."),
    6: Usecase(6, "Erklaervideo aus Audio", "audio", False, "generated_video", "faster",
               "Transkript -> Storyboard -> frontend-design erzeugt HTML/Motion-Graphics pro Beat "
               "-> Hyperframes rendert zu MP4. Kein Originalbild, alles generiert."),
    7: Usecase(7, "Audio + animiertes Video-Cover", "audio", False, "audio_cover", "faster",
               "Audioschnitt wie Usecase 1 + ein animiertes Cover (Standbild/Loop) via "
               "frontend-design -> Hyperframes, das ueber die Tonspur gelegt wird."),
    8: Usecase(8, "Werbeclip / Ad (kurz, 15-60s)", "audio", False, "ad_clip", "faster",
               "Kurzer Brief/VO -> Transkript -> Ad-Storyboard (Hook->Nutzen->CTA). Generierung "
               "via OpenMontage clip-factory (<OPENMONTAGE_DIR>) ODER frontend-design+Hyperframes "
               "mit Brand-Tokens; Musikbett + CTA-Endcard. ACHTUNG kommerziell: Asset-/Modell-Lizenzen "
               "pruefen (manche lokale Video-Modelle/Stock sind non-commercial)."),
}


def load_config() -> dict:
    cfg_path = HERE / "config" / "settings.json"
    if not cfg_path.exists():
        raise SystemExit(
            "config/settings.json fehlt. Kopiere config/settings.example.json -> "
            "config/settings.json und trage deine Pfade/Engines/Compute ein."
        )
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def resolve_engine(uc: Usecase, num_speakers: int | None, cfg: dict) -> str:
    """whisperx sobald Multi-Speaker (per Usecase ODER --num-speakers > 1)."""
    if uc.multi_speaker or (num_speakers and num_speakers > 1):
        return cfg["engines"]["multi_speaker"]
    return uc.engine


def pick_model(engine: str, on_mac: bool, cfg: dict) -> str:
    key = f"{engine if engine != 'faster' else 'faster'}_{'mac' if on_mac else 'local'}"
    key = ("whisperx_" if engine == "whisperx" else "faster_") + ("mac" if on_mac else "local")
    return cfg["models"].get(key, "medium")


# --------------------------------------------------------------------------- #
# prepare: Transkription (geroutet) + pack
# --------------------------------------------------------------------------- #
def prepare(media: Path, mode: int, project: str | None, num_speakers: int | None) -> int:
    cfg = load_config()
    uc = USECASES[mode]
    engine = resolve_engine(uc, num_speakers, cfg)

    # Projekt-/Edit-Verzeichnis: in ai-media-editor/projects/<name>/edit
    proj_name = project or media.stem
    proj_dir = HERE / "projects" / proj_name
    edit_dir = proj_dir / "edit"
    edit_dir.mkdir(parents=True, exist_ok=True)
    # Quelle ins Projekt spiegeln, falls noch nicht dort
    local_media = proj_dir / media.name
    if media.resolve() != local_media.resolve():
        if not local_media.exists():
            local_media.write_bytes(media.read_bytes())

    hf_token = cfg.get("hf_token") or None
    if engine == "whisperx" and not hf_token:
        print("  [warn] WhisperX-Diarisierung ohne HF-Token -> alle Worte = speaker_0 "
              "(Sprechertrennung inaktiv). Token in config/settings.json eintragen.")

    json_path: Path | None = None
    prefer = cfg["compute"]["prefer"]

    # 1) Compute-Routing: Mac primaer
    if prefer == "mac":
        model = pick_model(engine, on_mac=True, cfg=cfg)
        print(f"  Engine={engine}  Modell={model}  Compute=Mac Studio (primaer)")
        json_path = mac_remote.run_remote(
            local_media, edit_dir, cfg["mac"], engine=engine, model=model,
            language=cfg["language"], num_speakers=num_speakers, hf_token=hf_token,
        )

    # 2) Lokaler Fallback (oder prefer == local)
    if json_path is None:
        model = pick_model(engine, on_mac=False, cfg=cfg)
        print(f"  Engine={engine}  Modell={model}  Compute=lokal (Laptop)")
        json_path = transcribe_local.transcribe_one(
            media=local_media, edit_dir=edit_dir, engine=engine, model=model,
            language=cfg["language"], device="auto", num_speakers=num_speakers,
            hf_token=hf_token,
        )

    # 3) pack_transcripts -> takes_packed.md
    venv_py = cfg["paths"]["venv_python"]
    pack = Path(cfg["paths"]["video_use"]) / "helpers" / "pack_transcripts.py"
    r = subprocess.run(
        [venv_py, str(pack), "--edit-dir", str(edit_dir)],
        capture_output=True, text=True,
    )
    print(r.stdout.strip())
    if r.returncode != 0:
        print(f"  [warn] pack_transcripts: {r.stderr.strip()[-300:]}")

    # Schnitt-Ansicht: Pausen als Schnittinformation (Kern jedes Usecases)
    cutview = Path(HERE) / "tools" / "cut_view.py"
    subprocess.run([venv_py, str(cutview), "--edit-dir", str(edit_dir)],
                   capture_output=True, text=True)
    cut_view_path = edit_dir / "cut_view.md"

    # Multi-Speaker: tokenfreie Diarisierung per LLM-Zuordnung vorbereiten
    diar_prompt = None
    is_multi = uc.multi_speaker or (num_speakers and num_speakers > 1)
    if is_multi and engine != "whisperx":
        prompts = diarize_llm.build_prompt(edit_dir, max_speakers=num_speakers)
        diar_prompt = prompts[0] if prompts else None

    takes = edit_dir / "takes_packed.md"
    print("\n" + "=" * 70)
    print(f"  USECASE {uc.mode}: {uc.label}")
    print(f"  Projekt:        {proj_dir}")
    print(f"  Transkript:     {json_path}")
    print(f"  Lesefassung:    {takes}  (das liest der Editor-Agent)")
    print(f"  Schnitt-Ansicht:{cut_view_path}  (Pausen = Schnittinfo)")
    print("=" * 70)
    if diar_prompt:
        print(f"  Diarisierung:   {diar_prompt}")
        print("   -> Tokenfrei: Claude Code ordnet Sprecher zu (kein HF-Token).")
        print("      1) Lies den Prompt + <stem>.phrases.json")
        print("      2) Schreibe <stem>.labels.json ({\"i\":idx,\"speaker\":int})")
        print("      3) python stt/diarize_llm.py apply --edit-dir <dir> --stem <stem> --labels <labels>")
    print("  Naechste Schritte (Claude Code faehrt sie):")
    for line in _wrap(uc.next_steps):
        print("   " + line)
    print("=" * 70)
    return 0


def _wrap(text: str, width: int = 64) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


# --------------------------------------------------------------------------- #
# frames: Video → zeitgestempelte Frames (Video-Scatterer)
# --------------------------------------------------------------------------- #
def _resolve_video(target: str, project: str | None) -> tuple[Path, Path]:
    """target = Videodatei ODER Projektname. Liefert (video, edit_dir)."""
    p = Path(target)
    if p.exists() and p.is_file():
        proj_name = project or p.stem
        edit_dir = HERE / "projects" / proj_name / "edit"
        return p.resolve(), edit_dir
    # Sonst: Projektname -> Video im Projektordner suchen
    proj_dir = HERE / "projects" / target
    if not proj_dir.exists():
        sys.exit(f"Weder Datei noch Projekt gefunden: {target}")
    vids = sorted(f for f in proj_dir.iterdir()
                  if f.is_file() and f.suffix.lower() in VIDEO_EXTS)
    if not vids:
        sys.exit(f"Kein Video ({'/'.join(sorted(VIDEO_EXTS))}) in {proj_dir}")
    if len(vids) > 1:
        print(f"  [i] mehrere Videos in {proj_dir}, nehme: {vids[0].name}")
    return vids[0].resolve(), proj_dir / "edit"


def frames(target: str, project: str | None, every: float, frm: float | None,
           to: float | None, step: float | None, sheet: bool, cols: int,
           rows: int, width: int, max_frames: int, font: str | None,
           label: bool) -> int:
    video, edit_dir = _resolve_video(target, project)
    edit_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Video: {video}")
    return frame_view.run(video, edit_dir, every, frm, to, step, sheet,
                          cols, rows, width, max_frames, font, label)


# --------------------------------------------------------------------------- #
# modes / doctor
# --------------------------------------------------------------------------- #
def show_modes() -> int:
    print(f"{'#':>2}  {'Usecase':<34} {'Eingang':<7} {'Sprecher':<9} {'Engine':<9} Output")
    print("-" * 92)
    for uc in USECASES.values():
        spk = "mehrere" if uc.multi_speaker else "1"
        print(f"{uc.mode:>2}  {uc.label:<34} {uc.input_kind:<7} {spk:<9} {uc.engine:<9} {uc.output_kind}")
    return 0


def doctor() -> int:
    cfg = load_config()
    ok = True

    def check(name: str, cond: bool, hint: str = "") -> None:
        nonlocal ok
        mark = "OK " if cond else "XX "
        if not cond:
            ok = False
        print(f"  [{mark}] {name}" + (f"  -> {hint}" if (not cond and hint) else ""))

    # ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        check("ffmpeg (lokal)", True)
    except Exception:
        check("ffmpeg (lokal)", False, "ffmpeg installieren / PATH pruefen")

    # venv + video-use deps
    venv_py = cfg["paths"]["venv_python"]
    check("venv python", Path(venv_py).exists(), venv_py)
    for mod in ("faster_whisper", "requests", "librosa"):
        r = subprocess.run([venv_py, "-c", f"import {mod}"], capture_output=True, text=True)
        check(f"venv: {mod}", r.returncode == 0, "pip install im venv noch nicht fertig?")

    # Mac
    reachable = mac_remote.is_reachable(cfg["mac"])
    check("Mac Studio erreichbar", reachable)
    if reachable:
        r = subprocess.run(
            mac_remote._ssh_base(cfg["mac"]) + [
                mac_remote._target(cfg["mac"]),
                f"{cfg['mac']['venv_activate']} && python3 -c "
                "'import faster_whisper, whisperx; print(\"stt_ok\")'"
            ], capture_output=True, text=True, timeout=40,
        )
        check("Mac STT-Stack (faster-whisper + whisperx)", "stt_ok" in r.stdout)

    # video-use Helpers
    vu = Path(cfg["paths"]["video_use"])
    check("video-use geklont", (vu / "helpers" / "pack_transcripts.py").exists())

    # node / hyperframes
    try:
        r = subprocess.run(["node", "--version"], capture_output=True, text=True)
        major = int(r.stdout.strip().lstrip("v").split(".")[0])
        check(f"Node.js >= 22 (hyperframes)  [{r.stdout.strip()}]", major >= 22)
    except Exception:
        check("Node.js", False, "Node 22+ fuer Hyperframes")

    # HF-Token (nur Info)
    print(f"  [i ] HF-Token fuer WhisperX-Diarisierung: "
          f"{'gesetzt' if cfg.get('hf_token') else 'LEER (nur fuer Usecase 2/4 noetig)'}")

    print("\n  -> " + ("Alles bereit." if ok else "Es fehlen noch Komponenten (siehe XX)."))
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(description="Podcast/Video-Editor Orchestrator")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prepare", help="Transkribieren + packen fuer einen Usecase")
    p.add_argument("media", type=Path)
    p.add_argument("--mode", type=int, required=True, choices=list(USECASES))
    p.add_argument("--project", type=str, default=None)
    p.add_argument("--num-speakers", type=int, default=None)

    f = sub.add_parser("frames", help="Video → zeitgestempelte Frames (Video-Scatterer)")
    f.add_argument("target", type=str, help="Videodatei ODER Projektname")
    f.add_argument("--project", type=str, default=None)
    f.add_argument("--every", type=float, default=10.0, help="Übersichts-Rate in Sekunden (Default 10)")
    f.add_argument("--from", dest="frm", type=float, default=None, help="Zoom-Start (Sekunden)")
    f.add_argument("--to", type=float, default=None, help="Zoom-Ende (Sekunden)")
    f.add_argument("--step", type=float, default=None, help="Zoom-Schrittweite (Sekunden, z. B. 0.25)")
    f.add_argument("--step-ms", type=float, default=None, help="Zoom-Schrittweite in ms (Alternative zu --step)")
    f.add_argument("--contact-sheet", action="store_true", help="Übersicht als gekacheltes Sheet")
    f.add_argument("--cols", type=int, default=4)
    f.add_argument("--rows", type=int, default=4)
    f.add_argument("--width", type=int, default=640, help="Frame-Breite px (kleiner = sparsamer)")
    f.add_argument("--max-frames", type=int, default=60, help="Obergrenze Einzelframes (Token-Schutz)")
    f.add_argument("--font", type=str, default=None, help="TTF-Pfad für Zeitstempel (sonst Auto)")
    f.add_argument("--label", action="store_true",
                   help="Zeitstempel in Einzelframes einbrennen (Default aus; Sheets immer)")

    sub.add_parser("modes", help="Usecase-Tabelle")
    sub.add_parser("doctor", help="Umgebungs-Check")

    args = ap.parse_args()
    if args.cmd == "prepare":
        media = args.media.resolve()
        if not media.exists():
            sys.exit(f"Datei nicht gefunden: {media}")
        sys.exit(prepare(media, args.mode, args.project, args.num_speakers))
    elif args.cmd == "frames":
        step = args.step
        if args.step_ms is not None:
            step = args.step_ms / 1000.0
        sys.exit(frames(args.target, args.project, args.every, args.frm, args.to,
                        step, args.contact_sheet, args.cols, args.rows,
                        args.width, args.max_frames, args.font, args.label))
    elif args.cmd == "modes":
        sys.exit(show_modes())
    elif args.cmd == "doctor":
        sys.exit(doctor())


if __name__ == "__main__":
    main()
