"""QA der gerenderten Clips: ffprobe-Daten, Schwarz am Anfang/Ende, Prüfframes, Kontaktbogen.

Aufruf: python -m ai_media_editor.tools.qa_clips <clips-ordner> <ausgabe-ordner>
Schreibt qa.json, frames/<clip>_{anfang,mitte,ende,hoehepunkt}.jpg und VORSCHAU_kontaktbogen.jpg.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import numpy as np
except ImportError:  # pragma: no cover - optional in minimal test environments
    np = None  # type: ignore[assignment]

PEAK: dict[str, float] = {
    "01-weisse-frau": 17.5,
    "02-schleimgeist": 15.0,
    "03-riesenspinne": 16.7,
    "04-kleine-spinnen": 16.0,
    "05-kuerbis-lacht": 16.0,
    "06-scream-opfer": 12.0,
    "07-vampir-fledermaus": 15.0,
    "08-bettlakengespenst": 13.6,
    "09-silhouette": 20.0,
    "10-hexe-lockt": 16.0,
    "11-kobolde-schatz": 16.1,
}


def probe(f: str | Path) -> dict[str, Any]:
    out = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height,r_frame_rate,pix_fmt,nb_frames:format=duration",
            "-of", "json",
            str(f),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    d = json.loads(out)
    s: dict[str, Any] = d["streams"][0]
    return {**s, "duration": float(d["format"]["duration"])}


def luma(f: str | Path, t: float) -> tuple[float, int]:
    raw = subprocess.run(
        [
            "ffmpeg",
            "-v", "error",
            "-ss", f"{t:.3f}",
            "-i", str(f),
            "-frames:v", "1",
            "-vf", "scale=192:108,format=gray",
            "-f", "rawvideo",
            "-",
        ],
        capture_output=True,
        check=True,
    ).stdout
    if not raw:
        return 0.0, 0
    if np is not None:
        a = np.frombuffer(raw, np.uint8)
        return float(a.mean()), int(a.max())
    return float(sum(raw) / len(raw)), int(max(raw))


def grab(f: str | Path, t: float, out: str | Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-v", "error",
            "-y",
            "-ss", f"{t:.3f}",
            "-i", str(f),
            "-frames:v", "1",
            "-vf", "scale=640:-1",
            str(out),
        ],
        check=True,
    )


def build_xstack_layout(n: int, cols: int = 4) -> str:
    return "|".join(
        f"{'+'.join(['w0'] * (i % cols)) or '0'}_{'+'.join(['h0'] * (i // cols)) or '0'}"
        for i in range(n)
    )


def run_qa(
    src_dir: str | Path,
    dst_dir: str | Path,
    peak_map: dict[str, float] | None = None,
) -> dict[str, Any]:
    src, dst = Path(src_dir), Path(dst_dir)
    peaks_lookup = PEAK if peak_map is None else peak_map
    (dst / "frames").mkdir(parents=True, exist_ok=True)
    rep: dict[str, Any] = {}
    peaks: list[Path] = []
    for f in sorted(src.glob("*.mp4")):
        p = probe(f)
        d = float(p["duration"])
        first, last = luma(f, 0.0), luma(f, max(0.0, d - 0.1))
        for name, t in (("anfang", 0.5), ("mitte", d / 2.0), ("ende", max(0.0, d - 1.0))):
            grab(f, t, dst / "frames" / f"{f.stem}_{name}.jpg")
        pk = dst / "frames" / f"{f.stem}_hoehepunkt.jpg"
        grab(f, peaks_lookup.get(f.stem, d / 2.0), pk)
        peaks.append(pk)
        rep[f.stem] = {
            **p,
            "first_frame_luma_mean_max": first,
            "last_frame_luma_mean_max": last,
            "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
            "bytes": f.stat().st_size,
        }
        print(
            f"{f.stem:22s} {d:6.2f}s {p['width']}x{p['height']} {p['r_frame_rate']} "
            f"{p['codec_name']} {p['pix_fmt']} "
            f"erstes={first[0]:.2f}/{first[1]} letztes={last[0]:.2f}/{last[1]}"
        )
    (dst / "qa.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    if peaks:
        ins: list[str] = []
        for p_path in peaks:
            ins.extend(["-i", str(p_path)])
        n = len(peaks)
        layout = build_xstack_layout(n)
        subprocess.run(
            [
                "ffmpeg",
                "-v", "error",
                "-y",
                *ins,
                "-filter_complex",
                "".join(f"[{i}]" for i in range(n)) + f"xstack=inputs={n}:layout={layout}:fill=0x202020",
                "-frames:v", "1",
                str(dst / "VORSCHAU_kontaktbogen.jpg"),
            ],
            check=True,
        )
    return rep


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if len(args) < 2:
        raise SystemExit("Aufruf: python -m ai_media_editor.tools.qa_clips <clips-ordner> <ausgabe-ordner>")
    run_qa(Path(args[0]), Path(args[1]))


if __name__ == "__main__":
    main()
