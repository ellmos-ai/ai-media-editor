"""UC7-Finalisierung: animiertes Cover (Loop) über die volle Tonspur legen.

Hyperframes rendert ein kurzes, nahtlos loopendes Cover (z. B. 12 s). Dieses
Tool loopt das Cover-Video per ffmpeg über die gesamte Audiolänge und
kombiniert beides zu einem fertigen MP4 — wie ein YouTube-Musikvideo mit
Standbild/Loop-Cover.

Usage:
    python compose_cover.py --cover <cover_loop.mp4> --audio <podcast.m4a> \
        --out <final.mp4> [--fps 30] [--crf 20]
"""
from __future__ import annotations

import argparse
import math
import subprocess
import sys
from pathlib import Path


def ffprobe_duration(path: Path) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True,
        )
    except OSError:
        return 0.0
    if r.returncode != 0:
        return 0.0
    try:
        duration = float(r.stdout.strip())
    except ValueError:
        return 0.0
    return duration if math.isfinite(duration) and duration >= 0 else 0.0


def compose(cover: Path, audio: Path, out: Path, fps: int, crf: int) -> int:
    if not cover.is_file():
        sys.exit(f"Cover nicht gefunden: {cover}")
    if not audio.is_file():
        sys.exit(f"Audio nicht gefunden: {audio}")
    if out.resolve() in {cover.resolve(), audio.resolve()}:
        sys.exit("Ausgabedatei darf Eingabedateien nicht überschreiben.")
    if fps < 1 or not 0 <= crf <= 51:
        sys.exit("--fps muss >= 1 und --crf zwischen 0 und 51 sein.")
    out.parent.mkdir(parents=True, exist_ok=True)

    audio_dur = ffprobe_duration(audio)
    cover_dur = ffprobe_duration(cover)
    if cover_dur <= 0 or audio_dur <= 0:
        sys.exit("ffprobe konnte Cover- oder Audiodauer nicht bestimmen.")
    print(f"  Cover-Loop: {cover_dur:.1f}s  |  Audio: {audio_dur:.1f}s  "
          f"-> {audio_dur / cover_dur:.1f}x geloopt")

    # Cover unendlich loopen (-stream_loop -1), Audio bestimmt die Länge (-shortest).
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", str(cover),
        "-i", str(audio),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-r", str(fps),
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(out),
    ]
    print("  ffmpeg: loope Cover über Audio …", flush=True)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except OSError as exc:
        raise SystemExit(f"ffmpeg konnte nicht gestartet werden: {exc}") from exc
    if r.returncode != 0:
        print(r.stderr[-800:])
        sys.exit("ffmpeg fehlgeschlagen")

    final_dur = ffprobe_duration(out)
    mb = out.stat().st_size / (1024 * 1024)
    print(f"  fertig: {out}  ({final_dur:.1f}s, {mb:.1f} MB)")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="UC7: Cover-Loop über Tonspur legen")
    ap.add_argument("--cover", type=Path, required=True, help="Kurzes Cover-Loop-MP4 (Hyperframes)")
    ap.add_argument("--audio", type=Path, required=True, help="Podcast-Audio (volle Länge)")
    ap.add_argument("--out", type=Path, required=True, help="Ziel-MP4")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--crf", type=int, default=20)
    args = ap.parse_args()
    sys.exit(compose(args.cover, args.audio, args.out, args.fps, args.crf))


if __name__ == "__main__":
    main()
