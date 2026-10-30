"""Setzt die Einzelclips mit Schwarzpausen zu einem Loopvideo zusammen (optional mit Tonspur).

Aufruf: python -m ai_media_editor.tools.make_loop <loop.json> <clips-ordner> -o loop.mp4 [--pause 8] [--audio atmo.wav]
Reihenfolge und Pausenlänge kommen aus loop.json (Pause per --pause überschreibbar).
Ausgabe: H.264 yuv420p 1920x1080 30 fps; mit --audio zusätzlich AAC 48 kHz.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def build_ffmpeg_command(
    cfg: dict[str, Any],
    clips_dir: str | Path,
    out_path: str | Path,
    pause: float | None = None,
    audio: str | Path | None = None,
) -> tuple[list[str], float, float]:
    """Erzeugt das FFmpeg-Kommando, die effektive Pausenlänge (s) und die Gesamtdauer (s)."""
    pause_s = float(pause if pause is not None else cfg["pause_s"])
    order: list[str] = list(cfg["order"])
    if not order:
        raise ValueError("loop.json 'order' darf nicht leer sein")
    clips_root = Path(clips_dir)
    cmd: list[str] = ["ffmpeg", "-y", "-v", "error"]
    parts: list[str] = []
    for i, sid in enumerate(order):
        cmd += ["-i", str(clips_root / f"{sid}.mp4")]
        parts.append(f"[{i}:v]fps=30,format=yuv420p,setsar=1[v{i}];")
    n = len(order)
    flt = "".join(parts)
    flt += "".join(
        f"color=c=black:s=1920x1080:r=30:d={pause_s},format=yuv420p,setsar=1[p{i}];"
        for i in range(n)
    )
    flt += "".join(f"[v{i}][p{i}]" for i in range(n)) + f"concat=n={2 * n}:v=1:a=0[v]"
    if audio:
        cmd += ["-i", str(audio)]
    cmd += ["-filter_complex", flt, "-map", "[v]"]
    if audio:
        cmd += ["-map", f"{n}:a", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest"]
    cmd += [
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_path),
    ]
    durations = cfg.get("durations_s", {})
    total = sum(float(durations[s]) for s in order) + n * pause_s
    return cmd, pause_s, total


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        description="Setzt Einzelclips mit Schwarzpausen zu einem Loopvideo zusammen."
    )
    ap.add_argument("config", help="Pfad zur loop.json")
    ap.add_argument("clips", help="Ordner mit den gerenderten <sid>.mp4-Clips")
    ap.add_argument("-o", "--out", required=True, help="Ausgabe-MP4-Pfad")
    ap.add_argument("--pause", type=float, help="Schwarzpause in Sekunden (überschreibt loop.json)")
    ap.add_argument("--audio", help="Optionale Audiospur (z. B. atmo.wav)")
    a = ap.parse_args(argv)
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
    cmd, pause, total = build_ffmpeg_command(cfg, a.clips, a.out, pause=a.pause, audio=a.audio)
    subprocess.run(cmd, check=True)
    n = len(cfg["order"])
    print(f"Loop: {n} Clips, Pause {pause} s, Soll-Länge {total:.1f} s -> {a.out}")


if __name__ == "__main__":
    main()
