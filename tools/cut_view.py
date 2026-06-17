"""Schnitt-Ansicht: Pausen als explizite Schnittinformation.

Kernidee (vom User): Beim Schneiden geht es um sinnvolle Abschnitte, und
PAUSEN sind die wertvollste Schnittinformation. Diese Info steckt bereits
exakt im Scribe-JSON (spacing-Einträge + Wort-zu-Wort-Gaps), wird aber sonst
nur implizit genutzt. cut_view macht sie sichtbar und klassifiziert jede
Pause als Schnittkandidat.

Klassifikation (an video-use SKILL.md angelehnt):
  >= 0.80s   ✂✂  starker Schnitt  (sauberste Cuts)
  0.40-0.80  ✂   guter Schnitt
  0.15-0.40  ·   möglich (visuell/akustisch prüfen)
  < 0.15s        unsicher (mitten im Sprechfluss) — wird nicht als Cut gelistet

Zusätzlich markiert: lange Stille am ANFANG/ENDE (Trim-Kandidaten, z.B.
Soundcheck, Stille nach Stopp) und die längsten Pausen insgesamt.

Ausgabe: <edit>/cut_view.md  (lesbare Schnitt-Landkarte je Quelle)

Usage:
    python cut_view.py --edit-dir <dir> [--strong 0.8] [--good 0.4] [--weak 0.15]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def fmt(t: float) -> str:
    m = int(t // 60)
    s = t - m * 60
    return f"{m:02d}:{s:05.2f}"


def find_pauses(words: list[dict]) -> list[dict]:
    """Alle Pausen zwischen aufeinanderfolgenden 'word'-Tokens (Sekunden)."""
    kept = [w for w in words if w.get("type") == "word" and w.get("start") is not None]
    pauses = []
    for a, b in zip(kept, kept[1:]):
        gap = float(b["start"]) - float(a.get("end", a["start"]))
        if gap > 0:
            pauses.append({"at": float(a.get("end", a["start"])), "dur": gap,
                           "before": (b.get("text") or "").strip()})
    return pauses, kept


def classify(dur: float, strong: float, good: float, weak: float) -> tuple[str, str]:
    if dur >= strong:
        return "✂✂", "stark"
    if dur >= good:
        return "✂", "gut"
    if dur >= weak:
        return "·", "möglich"
    return "", "unsicher"


def build_cut_view(jf: Path, strong: float, good: float, weak: float) -> tuple[str, dict]:
    data = json.loads(jf.read_text(encoding="utf-8"))
    words = data.get("words", [])
    pauses, kept = find_pauses(words)
    if not kept:
        return f"## {jf.stem}\n  _kein Audio/keine Wörter_\n", {}

    audio_start = float(kept[0]["start"])
    audio_end = float(kept[-1].get("end", kept[-1]["start"]))

    # Abschnitte zwischen Schnittkandidaten (>= good) bilden
    cut_points = [p for p in pauses if p["dur"] >= good]
    n_strong = sum(1 for p in pauses if p["dur"] >= strong)
    n_good = sum(1 for p in pauses if good <= p["dur"] < strong)
    n_weak = sum(1 for p in pauses if weak <= p["dur"] < good)
    total_silence = sum(p["dur"] for p in pauses)
    longest = sorted(pauses, key=lambda p: -p["dur"])[:5]

    lines = [f"## {jf.stem}"]
    lines.append(f"  Dauer {fmt(audio_end - audio_start)} · {len(kept)} Wörter · "
                 f"Stille gesamt {total_silence:.1f}s")
    if audio_start >= 1.0:
        lines.append(f"  ⟦TRIM-START⟧ {audio_start:.1f}s Stille/Vorlauf vor dem ersten Wort")
    lines.append(f"  Schnittkandidaten: {n_strong}× stark (≥{strong}s) · "
                 f"{n_good}× gut · {n_weak}× möglich")
    lines.append("")
    lines.append("  Längste Pausen (beste Schnitte):")
    for p in longest:
        mark, _ = classify(p["dur"], strong, good, weak)
        lines.append(f"    {mark or '·'} {fmt(p['at'])}  {p['dur']:.2f}s   → vor \"{p['before'][:40]}\"")
    lines.append("")
    return "\n".join(lines), {
        "stem": jf.stem, "n_strong": n_strong, "n_good": n_good,
        "n_weak": n_weak, "cut_points": len(cut_points),
        "total_silence": round(total_silence, 1),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Pausen als Schnitt-Ansicht")
    ap.add_argument("--edit-dir", type=Path, required=True)
    ap.add_argument("--strong", type=float, default=0.8)
    ap.add_argument("--good", type=float, default=0.4)
    ap.add_argument("--weak", type=float, default=0.15)
    ap.add_argument("-o", "--output", type=Path, default=None)
    args = ap.parse_args()

    edit_dir = args.edit_dir.resolve()
    tdir = edit_dir / "transcripts"
    jfs = sorted(tdir.glob("*.json"))
    if not jfs:
        raise SystemExit(f"keine Transkripte in {tdir}")

    blocks = ["# Schnitt-Ansicht — Pausen als Schnittinformation", "",
              "✂✂ stark (≥0.8s) · ✂ gut (≥0.4s) · · möglich (≥0.15s). "
              "Schneide an den stärksten Pausen; ⟦TRIM⟧ = Vorlauf/Stille zum Wegschneiden.", ""]
    stats = []
    for jf in jfs:
        block, st = build_cut_view(jf, args.strong, args.good, args.weak)
        blocks.append(block)
        if st:
            stats.append(st)

    out = args.output or (edit_dir / "cut_view.md")
    out.write_text("\n".join(blocks), encoding="utf-8")
    print(f"Schnitt-Ansicht: {out}")
    for s in stats:
        print(f"  {s['stem']}: {s['cut_points']} Schnittpunkte (≥{args.good}s), "
              f"{s['n_strong']} stark, {s['total_silence']}s Stille")


if __name__ == "__main__":
    main()
