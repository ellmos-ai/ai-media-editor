"""Frame-Ansicht: Video in zeitgestempelte Einzelbilder zerlegen ("Video-Scatterer").

Kernidee (vom User): Der Editor-Agent schneidet bisher BLIND nach Transkript/
Pausen — er "sieht" das Bild nicht. Dieses Tool gibt ihm die zweite Modalität:
es zerlegt ein Video in Frames und gibt nur alle paar Sekunden ein Bild aus,
jeweils mit EINGEBRANNTEM Zeitstempel. So kann ein multimodales LLM den
Bildverlauf beurteilen und eine visuelle Beobachtung direkt in einen Schnitt-/
Overlay-Timestamp zurückübersetzen.

Zwei Pässe (coarse-to-fine, token-effizient):
  1. ÜBERSICHT  — grobe Rate (z. B. alle 10 s) über das ganze Video.
     Optional als Contact-Sheet (gekachelte Thumbnails, sehr sparsam).
  2. ZOOM       — bei interessantem Bereich feiner nachsampeln:
     --from x --to y --step z  (Sekunden, z. B. --step 0.25)  oder  --step-ms l.

Der Zeitstempel kann bei Einzelframes per ffmpeg `drawtext` eingebrannt werden
(Fallback: Zeit in Dateiname + `frame_view.md`). Contact-Sheets benötigen einen
funktionierenden `drawtext`-Filter, weil einzelne Kacheln sonst nicht eindeutig
zugeordnet werden können. Zeitbasis = Sekunden ab Videostart → identisch mit der
Scribe-JSON-Zeitbasis, damit Bildbeobachtungen auf Schnittkanten mappen.

Ausgabe:
  <edit>/frames/        ← die Einzelbilder/Contact-Sheets (gitignored)
  <edit>/frame_view.md  ← Index: welches Bild = welche Zeit (der Agent liest das)

Usage (standalone):
    python frame_view.py --video <datei> --edit-dir <dir> [--every 10] [--width 640]
    python frame_view.py --video <datei> --edit-dir <dir> --from 30 --to 45 --step 0.25
    python frame_view.py --video <datei> --edit-dir <dir> --contact-sheet --cols 4 --rows 4
"""
from __future__ import annotations

import argparse
import math
import subprocess
import sys
from pathlib import Path

# Übliche Font-Pfade je Plattform (erster existierender wird genommen).
_FONT_CANDIDATES = [
    "C:/Windows/Fonts/consola.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
]


# --------------------------------------------------------------------------- #
# Helfer
# --------------------------------------------------------------------------- #
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


def fmt_clock(t: float) -> str:
    """Sekunden -> MM:SS.s (lesbarer Zeitstempel)."""
    m = int(t // 60)
    s = t - m * 60
    return f"{m:02d}:{s:04.1f}"


def label_text(t: float) -> str:
    """Im Bild eingebrannter Text: Uhrzeit + Sekunden (kein '=' wegen drawtext)."""
    return f"{fmt_clock(t)}  {t:.1f}s"


def frame_name(t: float) -> str:
    """Sortierbarer, exakter Dateiname aus Millisekunden."""
    return f"f_{int(round(t * 1000)):09d}ms.jpg"


def find_font(user_font: str | None) -> str | None:
    if user_font:
        return user_font if Path(user_font).exists() else None
    for cand in _FONT_CANDIDATES:
        if Path(cand).exists():
            return cand
    return None


def _q_text(s: str) -> str:
    """Literalen Textwert für drawtext bauen: in Single-Quotes wrappen und
    Sonderzeichen escapen. Empirisch nötig auf Windows-ffmpeg: Doppelpunkt
    muss AUCH innerhalb der Quotes als \\: escaped werden, sonst bricht der
    Filtergraph-Parser am Doppelpunkt ab.
    """
    s = s.replace("\\", "\\\\")
    s = s.replace("'", "\\'")
    s = s.replace(":", "\\:")
    s = s.replace("%", "\\%")
    return f"text='{s}'"


def _q_fontfile(p: str) -> str:
    """Font-Pfad: Forward-Slashes, Laufwerks-Doppelpunkt escapen, in Quotes."""
    p = str(p).replace("\\", "/").replace(":", "\\:")
    return f"fontfile='{p}'"


def _drawtext(text_field: str, font: str | None, width: int) -> str:
    """drawtext-Filterglied mit lesbarem Box-Hintergrund.

    text_field ist ein fertiges `text='...'`-Segment (literal via _q_text
    oder roh mit pts-Expansion für das Contact-Sheet).
    """
    fontsize = max(16, width // 26)
    parts = []
    if font:
        parts.append(_q_fontfile(font))
    parts.append(text_field)
    parts.append("fontcolor=white")
    parts.append(f"fontsize={fontsize}")
    parts.append("box=1")
    parts.append("boxcolor=black@0.55")
    parts.append("boxborderw=8")
    parts.append("x=12")
    parts.append("y=12")
    return "drawtext=" + ":".join(parts)


# --------------------------------------------------------------------------- #
# Einzelframe-Extraktion (Übersicht + Zoom)
# --------------------------------------------------------------------------- #
def extract_frame(video: Path, t: float, out: Path, width: int, font: str | None,
                  label: bool) -> bool:
    """Einen Frame bei Sekunde t extrahieren.

    label=False (Default): saubere Pixel, Zeit nur über Dateiname + Markdown.
    label=True: Zeitstempel oben links einbrennen (Fallback ohne Text bei
    drawtext-Fehler). Rückgabe: True wenn der gewünschte Modus klappte,
    False wenn auf den textlosen Fallback ausgewichen wurde.
    """
    scale = f"scale={width}:-2"

    def _shot(vf: str) -> bool:
        out.unlink(missing_ok=True)
        try:
            r = subprocess.run(
                ["ffmpeg", "-nostdin", "-y", "-ss", f"{t:.3f}", "-i", str(video),
                 "-frames:v", "1", "-vf", vf, "-q:v", "3", str(out)],
                capture_output=True, text=True,
            )
        except OSError:
            return False
        return r.returncode == 0 and out.exists()

    if not label:
        return _shot(scale)
    if _shot(f"{scale},{_drawtext(_q_text(label_text(t)), font, width)}"):
        return True
    # Fallback: ohne drawtext (Zeit bleibt im Dateinamen + Markdown)
    _shot(scale)
    return False


def gen_timestamps(start: float, stop: float, step: float, max_frames: int) -> tuple[list[float], bool]:
    if not all(math.isfinite(value) for value in (start, stop, step)):
        raise ValueError("Frame-Zeiten müssen endliche Zahlen sein.")
    if start < 0 or stop < start:
        raise ValueError("Frame-Bereich muss 0 <= Start <= Ende erfüllen.")
    if step <= 0:
        raise ValueError("Frame-Schrittweite muss größer als 0 sein.")
    if max_frames < 1:
        raise ValueError("--max-frames muss mindestens 1 sein.")
    ts: list[float] = []
    # Float-Akkumulation vermeiden: index-basiert
    i = 0
    while True:
        cur = start + i * step
        if cur > stop + 1e-6:
            break
        ts.append(round(cur, 3))
        i += 1
        if len(ts) > max_frames:
            return ts[:max_frames], True
    capped = False
    return ts, capped


def sample_frames(video: Path, frames_dir: Path, timestamps: list[float],
                  width: int, font: str | None, label: bool) -> tuple[list[tuple[float, str]], int]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    entries: list[tuple[float, str]] = []
    burn_fail = 0
    for t in timestamps:
        out = frames_dir / frame_name(t)
        ok = extract_frame(video, t, out, width, font, label)
        if label and not ok:
            burn_fail += 1
        if out.exists():
            entries.append((t, f"frames/{out.name}"))
    return entries, burn_fail


# --------------------------------------------------------------------------- #
# Contact-Sheet (gekachelte Übersicht, ein ffmpeg-Pass)
# --------------------------------------------------------------------------- #
def contact_sheet(video: Path, frames_dir: Path, every: float, cols: int, rows: int,
                  width: int, font: str | None) -> list[str]:
    """Gekachelte Thumbnails mit eingebranntem pts-Zeitstempel je Frame.

    Sehr token-sparsamer Übersichts-Pass: viele Mini-Frames in einem Bild.
    """
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob("sheet_*.jpg"):
        old.unlink()
    thumb_w = max(160, width // 3)
    # %{pts:hms} brennt die echte Quellzeit je Frame ein. In Single-Quotes
    # wrappen UND den Doppelpunkt der pts-Funktion escapen (Windows-ffmpeg).
    dt = _drawtext("text='%{pts\\:hms}'", font, thumb_w)
    vf = f"fps=1/{every},scale={thumb_w}:-2,{dt},tile={cols}x{rows}"
    out_pat = str(frames_dir / "sheet_%03d.jpg")
    cmd = ["ffmpeg", "-nostdin", "-y", "-i", str(video), "-vf", vf, "-q:v", "3", out_pat]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except OSError:
        return []
    if r.returncode != 0:
        for partial in frames_dir.glob("sheet_*.jpg"):
            partial.unlink()
        return []
    sheets = sorted(p.name for p in frames_dir.glob("sheet_*.jpg"))
    return sheets


# --------------------------------------------------------------------------- #
# Markdown-Index
# --------------------------------------------------------------------------- #
def write_markdown(edit_dir: Path, video: Path, duration: float, mode: str,
                   entries: list[tuple[float, str]], sheets: list[str],
                   every: float | None, zoom: tuple[float, float, float] | None,
                   burn_fail: int, capped: bool, max_frames: int) -> Path:
    lines = ["# Frame-Ansicht — Bildverlauf mit Zeitstempel", ""]
    lines.append(f"Quelle: `{video.name}` · Dauer {fmt_clock(duration)} ({duration:.1f}s)")
    lines.append(
        "**Zeit ↔ Bild:** Der Dateiname kodiert die exakte Quellzeit "
        "(`f_<ms>ms.jpg`, ms ab Start = Scribe-/Schnitt-Zeitbasis); die Tabelle unten "
        "mappt jeden Frame auf MM:SS.s + Sekunde. Beim Öffnen eines Frames per Read-Tool "
        "ist die Zeit also über Pfad + Tabelle eindeutig. **Contact-Sheets** tragen die "
        "Zeit zusätzlich je Kachel eingebrannt (sonst nicht unterscheidbar). Einzelframes "
        "nur mit `--label` einbrennen (überdeckt sonst evtl. Lower-Third-Region)."
    )
    lines.append(
        "Bildinhalt beurteilen, dann für einen Bereich feiner nachsampeln: "
        "`--from x --to y --step z` (oder `--step-ms l`)."
    )
    if burn_fail:
        lines.append(
            f"> Hinweis: bei {burn_fail} Frame(s) konnte der Zeitstempel nicht eingebrannt "
            "werden (kein Font/drawtext) — Zeit steht im Dateinamen + dieser Tabelle."
        )
    if capped:
        lines.append(
            f"> ⚠ Auf `--max-frames {max_frames}` begrenzt — nicht das ganze Video/der "
            "ganze Bereich abgedeckt. Rate vergröbern (`--every`/`--step`) oder Cap erhöhen."
        )
    lines.append("")

    if sheets:
        lines.append(f"## Übersicht (Contact-Sheet, alle {every:g}s)")
        for s in sheets:
            lines.append(f"![sheet](frames/{s})")
        lines.append("")

    if entries:
        if mode == "zoom" and zoom:
            f, t, st = zoom
            lines.append(f"## Zoom {fmt_clock(f)}–{fmt_clock(t)} (Schritt {st:g}s) · {len(entries)} Frames")
        else:
            lines.append(f"## Übersicht (alle {every:g}s) · {len(entries)} Frames")
        lines.append("")
        lines.append("| Zeit | Sekunde | Bild |")
        lines.append("|---|---|---|")
        for tt, rel in entries:
            lines.append(f"| {fmt_clock(tt)} | {tt:.1f}s | `{rel}` |")
        lines.append("")
        lines.append("Einbettungen (zum direkten Ansehen):")
        for tt, rel in entries:
            lines.append(f"![{fmt_clock(tt)}]({rel})")
        lines.append("")

    out = edit_dir / "frame_view.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


# --------------------------------------------------------------------------- #
# Orchestrierung (auch von editor.py importiert)
# --------------------------------------------------------------------------- #
def run(video: Path, edit_dir: Path, every: float, frm: float | None, to: float | None,
        step: float | None, sheet: bool, cols: int, rows: int, width: int,
        max_frames: int, font: str | None, label: bool = False) -> int:
    video = video.resolve()
    edit_dir = edit_dir.resolve()
    if not video.is_file():
        print(f"  [XX] Video nicht gefunden: {video}")
        return 1
    if not math.isfinite(every) or every <= 0:
        raise ValueError("--every muss eine endliche Zahl größer als 0 sein.")
    if (frm is None) != (to is None):
        raise ValueError("--from und --to müssen gemeinsam angegeben werden.")
    if step is not None and (not math.isfinite(step) or step <= 0):
        raise ValueError("--step/--step-ms muss größer als 0 sein.")
    if cols < 1 or rows < 1:
        raise ValueError("--cols und --rows müssen mindestens 1 sein.")
    if width < 16:
        raise ValueError("--width muss mindestens 16 Pixel betragen.")
    if max_frames < 1:
        raise ValueError("--max-frames muss mindestens 1 sein.")
    (edit_dir / "frame_view.md").unlink(missing_ok=True)
    duration = ffprobe_duration(video)
    if duration <= 0:
        print("  [warn] konnte Dauer nicht lesen (ffprobe) — fahre dennoch fort.")
    font_path = find_font(font)
    frames_dir = edit_dir / "frames"

    sheets: list[str] = []
    entries: list[tuple[float, str]] = []
    burn_fail = 0
    capped = False
    zoom = None

    if frm is not None and to is not None:
        # ZOOM-Pass
        mode = "zoom"
        st = step if step is not None else 0.5
        ts, capped = gen_timestamps(frm, to, st, max_frames)
        entries, burn_fail = sample_frames(video, frames_dir, ts, width, font_path, label)
        zoom = (frm, to, st)
        print(f"  Zoom {fmt_clock(frm)}–{fmt_clock(to)} Schritt {st:g}s → {len(entries)} Frames")
    elif sheet:
        # ÜBERSICHT als Contact-Sheet
        mode = "sheet"
        sheets = contact_sheet(video, frames_dir, every, cols, rows, width, font_path)
        print(f"  Contact-Sheet alle {every:g}s ({cols}x{rows}) → {len(sheets)} Blatt/Blätter")
    else:
        # ÜBERSICHT als Einzelframes
        mode = "overview"
        stop = duration if duration > 0 else every * max_frames
        ts, capped = gen_timestamps(0.0, stop, every, max_frames)
        entries, burn_fail = sample_frames(video, frames_dir, ts, width, font_path, label)
        print(f"  Übersicht alle {every:g}s → {len(entries)} Frames"
              + ("  (Zeitstempel eingebrannt)" if label else "  (Zeit via Dateiname+Index)"))

    if not entries and not sheets:
        print("  [XX] ffmpeg hat keine Frames erzeugt.")
        return 1

    if label and font_path is None:
        print("  [i ] kein expliziter Font gefunden — ffmpeg-Standardfont wird versucht; "
              "bei Fehler bleibt die Zeit in Dateiname + frame_view.md.")
    if label and burn_fail:
        print(f"  [warn] {burn_fail} Frame(s) ohne eingebrannten Text (drawtext) — "
              "Zeit bleibt in Dateiname + frame_view.md.")

    out = write_markdown(edit_dir, video, duration, mode, entries, sheets,
                         every, zoom, burn_fail, capped, max_frames)
    print(f"  Frame-Ansicht: {out}")
    if capped:
        print(f"  [warn] auf --max-frames {max_frames} begrenzt — Rate vergröbern oder Cap erhöhen.")
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description="Video → zeitgestempelte Frames (Video-Scatterer)")
    ap.add_argument("--video", type=Path, required=True, help="Quell-Video")
    ap.add_argument("--edit-dir", type=Path, required=True, help="Projekt-Edit-Verzeichnis")
    ap.add_argument("--every", type=float, default=10.0, help="Übersichts-Rate in Sekunden (Default 10)")
    ap.add_argument("--from", dest="frm", type=float, default=None, help="Zoom-Start (Sekunden)")
    ap.add_argument("--to", type=float, default=None, help="Zoom-Ende (Sekunden)")
    ap.add_argument("--step", type=float, default=None, help="Zoom-Schrittweite (Sekunden, z. B. 0.25)")
    ap.add_argument("--step-ms", type=float, default=None, help="Zoom-Schrittweite in Millisekunden (Alternative zu --step)")
    ap.add_argument("--contact-sheet", action="store_true", help="Übersicht als gekacheltes Sheet")
    ap.add_argument("--cols", type=int, default=4, help="Contact-Sheet: Spalten")
    ap.add_argument("--rows", type=int, default=4, help="Contact-Sheet: Zeilen")
    ap.add_argument("--width", type=int, default=640, help="Frame-Breite px (Default 640, kleiner = sparsamer)")
    ap.add_argument("--max-frames", type=int, default=60, help="Obergrenze Einzelframes (Token-Schutz)")
    ap.add_argument("--font", type=str, default=None, help="TTF-Pfad für den Zeitstempel (sonst Auto)")
    ap.add_argument("--label", action="store_true",
                    help="Zeitstempel in Einzelframes einbrennen (Default aus; Sheets immer)")
    args = ap.parse_args()

    step = args.step
    if args.step_ms is not None:
        step = args.step_ms / 1000.0
    sys.exit(run(args.video, args.edit_dir, args.every, args.frm, args.to, step,
                 args.contact_sheet, args.cols, args.rows, args.width,
                 args.max_frames, args.font, args.label))


if __name__ == "__main__":
    main()
