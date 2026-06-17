"""Tokenfreie Sprecher-Diarisierung per LLM-Zuordnung (MetaMedia-Weg).

Statt akustischer Diarisierung (pyannote → gated HF-Token) ordnet ein LLM die
Sprecher aus dem TRANSKRIPT-INHALT zu: Anrede, Rollen, Frage/Antwort-Dynamik,
Themenübergaben, Pausenmuster. Das ist der Ansatz aus MetaMedia-Regelwerk v1.1
("Sprecher aus dem Text", kein Token nötig).

Ablauf (zwei Schritte):
  1. build_prompt(edit_dir) — liest die Scribe-Transkripte (alle speaker_0),
     gruppiert in Phrasen (Pausen-basiert) und schreibt:
       <edit>/diarization/<stem>.phrases.json   (nummerierte Phrasen + Zeiten)
       <edit>/diarization/<stem>.prompt.md       (Anweisung für das LLM)
  2. apply_labels(edit_dir, stem, labels) — schreibt die zugeordneten Sprecher
     ZEITBASIERT zurück ins Scribe-JSON (jedes Wort im Phrasen-Zeitfenster
     bekommt die Sprecher-ID) und re-packt via pack_transcripts.

Das LLM kann sein:
  - Claude Code selbst (der Editor-Agent liest prompt.md + phrases.json,
    erzeugt labels.json, ruft apply). Kein Key, kein Token. Default.
  - Eine lokale LLM (Mac Ollama / Buddha-API) für automatische Zuordnung.

Usage:
    python diarize_llm.py prepare --edit-dir <dir> [--max-speakers N] [--silence 0.4]
    python diarize_llm.py apply   --edit-dir <dir> --stem <name> --labels <labels.json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# pack_transcripts (Re-Pack) aus video-use wiederverwenden
def _load_packer():
    try:
        cfg = json.loads((Path(__file__).resolve().parent.parent / "config" / "settings.json").read_text(encoding="utf-8"))
        vu = Path(cfg["paths"]["video_use"]) / "helpers"
    except Exception:
        import os
        vu_root = os.environ.get("VIDEO_USE_DIR")
        if not vu_root:
            raise RuntimeError(
                "video-use-Pfad nicht konfiguriert: paths.video_use in config/settings.json "
                "setzen (siehe settings.example.json) oder Umgebungsvariable VIDEO_USE_DIR."
            )
        vu = Path(vu_root) / "helpers"
    sys.path.insert(0, str(vu))
    import pack_transcripts  # noqa: E402
    return pack_transcripts


_SENT_END = (".", "?", "!", "…")


def segment_sentences(words: list[dict], silence: float = 0.4) -> list[dict]:
    """Segmentiert die Wortliste SATZ-fein: Schnitt an Satzende-Zeichen ODER
    Pause >= silence. Feiner als Pausen-Phrasen — nötig, weil Sprecherwechsel
    in flüssigen Dialogen oft an Satzgrenzen OHNE große Pause liegen
    (z. B. "...langes Dokument." | "Oh ja." | "Über 100 Seiten.").
    """
    segs: list[dict] = []
    cur: list[str] = []
    start: float | None = None
    prev_end: float | None = None

    def flush(end: float | None) -> None:
        nonlocal cur, start
        if cur and start is not None:
            segs.append({"start": start, "end": end if end is not None else start,
                         "text": " ".join(cur).replace(" ,", ",").replace(" .", ".")
                                 .replace(" ?", "?").replace(" !", "!")})
        cur, start = [], None

    for w in words:
        if w.get("type") != "word":
            continue
        ws, we = w.get("start"), w.get("end")
        txt = (w.get("text") or "").strip()
        if ws is None or not txt:
            continue
        # Pause zum vorherigen Wort -> Schnitt
        if prev_end is not None and start is not None and ws - prev_end >= silence:
            flush(prev_end)
        if start is None:
            start = ws
        cur.append(txt)
        prev_end = we if we is not None else ws
        # Satzende -> Schnitt
        if txt[-1] in _SENT_END:
            flush(prev_end)
    flush(prev_end)
    return segs


def build_prompt(edit_dir: Path, max_speakers: int | None = None, silence: float = 0.4) -> list[Path]:
    """Erzeugt pro Transkript einen Diarisierungs-Prompt + Phrasenliste."""
    transcripts_dir = edit_dir / "transcripts"
    out_dir = edit_dir / "diarization"
    out_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for jf in sorted(transcripts_dir.glob("*.json")):
        data = json.loads(jf.read_text(encoding="utf-8"))
        words = data.get("words", [])
        phrases = segment_sentences(words, silence=silence)
        # Nummerierte, kompakte Phrasenliste
        items = [
            {"i": i, "start": round(p["start"], 2), "end": round(p["end"], 2), "text": p["text"]}
            for i, p in enumerate(phrases)
        ]
        phrases_path = out_dir / f"{jf.stem}.phrases.json"
        phrases_path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")

        spk_hint = (f"Es sind genau {max_speakers} Sprecher." if max_speakers
                    else "Bestimme die Anzahl der Sprecher selbst (meist 2-4).")
        listing = "\n".join(f"[{it['i']:>3}] ({it['start']:>7.2f}-{it['end']:>7.2f}) {it['text']}" for it in items)
        prompt = f"""# Sprecher-Diarisierung per LLM — {jf.stem}

Ordne jede Phrase einem Sprecher zu. {spk_hint}

**Hinweise zur Zuordnung:**
- Nutze Inhalt, Anrede ("Frau X", "Herr Y"), Frage/Antwort-Dynamik, Rollen
  (Moderator stellt Fragen, Gast antwortet), Themenübergaben, Pausen
  (große Zeitsprünge zwischen Phrasen = oft Sprecherwechsel).
- Sprecher-IDs als 0-basierte Ganzzahlen: 0, 1, 2, ...
  Konvention: Moderator/Host meist 0, erster Gast 1, usw.
- Im Zweifel ordne der bisher wahrscheinlichsten Stimme zu (kein "unbekannt").

**Ausgabe:** Schreibe eine Datei `{jf.stem}.labels.json` mit einem Array von
Objekten `{{"i": <phrasen-index>, "speaker": <int>}}` — für JEDE Phrase genau
einen Eintrag. Dann ausführen:
    python diarize_llm.py apply --edit-dir "<edit_dir>" --stem "{jf.stem}" --labels "<pfad/{jf.stem}.labels.json>"

## Phrasen ({len(items)})
{listing}
"""
        prompt_path = out_dir / f"{jf.stem}.prompt.md"
        prompt_path.write_text(prompt, encoding="utf-8")
        written.append(prompt_path)
        print(f"  Diarisierungs-Prompt: {prompt_path}  ({len(items)} Phrasen)")
    return written


def apply_labels(edit_dir: Path, stem: str, labels_path: Path) -> Path:
    """Schreibt Sprecher zeitbasiert ins Scribe-JSON zurück und re-packt."""
    packer = _load_packer()
    out_dir = edit_dir / "diarization"
    phrases = json.loads((out_dir / f"{stem}.phrases.json").read_text(encoding="utf-8"))
    raw_labels = json.loads(Path(labels_path).read_text(encoding="utf-8"))

    # labels: Liste [{"i":..,"speaker":..}] ODER Mapping {"0":1,...}
    label_map: dict[int, int] = {}
    if isinstance(raw_labels, dict):
        label_map = {int(k): int(v) for k, v in raw_labels.items()}
    else:
        for e in raw_labels:
            label_map[int(e["i"])] = int(e["speaker"])

    # Zeit-Segmente bauen: (start, end, speaker_id)
    segments: list[tuple[float, float, str]] = []
    for p in phrases:
        spk = label_map.get(int(p["i"]), 0)
        segments.append((float(p["start"]), float(p["end"]), f"speaker_{spk}"))

    def speaker_at(t: float) -> str | None:
        for s, e, spk in segments:
            if s <= t <= e:
                return spk
        return None

    jf = edit_dir / "transcripts" / f"{stem}.json"
    data = json.loads(jf.read_text(encoding="utf-8"))
    last = "speaker_0"
    changed = 0
    for w in data.get("words", []):
        t = w.get("start")
        if t is None:
            w["speaker_id"] = last
            continue
        spk = speaker_at(float(t)) or last
        if w.get("speaker_id") != spk:
            changed += 1
        w["speaker_id"] = spk
        last = spk
    jf.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    n_spk = len({s for _, _, s in segments})
    print(f"  Sprecher angewendet: {n_spk} Sprecher, {changed} Wörter umgelabelt -> {jf.name}")

    # Re-Pack
    import subprocess
    cfg = json.loads((Path(__file__).resolve().parent.parent / "config" / "settings.json").read_text(encoding="utf-8"))
    venv_py = cfg["paths"]["venv_python"]
    pack = Path(cfg["paths"]["video_use"]) / "helpers" / "pack_transcripts.py"
    subprocess.run([venv_py, str(pack), "--edit-dir", str(edit_dir)], check=False)
    return jf


def main() -> None:
    ap = argparse.ArgumentParser(description="Tokenfreie Diarisierung per LLM-Zuordnung")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare", help="Prompt + Phrasen erzeugen")
    p.add_argument("--edit-dir", type=Path, required=True)
    p.add_argument("--max-speakers", type=int, default=None)
    p.add_argument("--silence", type=float, default=0.4)
    a = sub.add_parser("apply", help="Sprecher-Labels anwenden")
    a.add_argument("--edit-dir", type=Path, required=True)
    a.add_argument("--stem", type=str, required=True)
    a.add_argument("--labels", type=Path, required=True)
    args = ap.parse_args()

    if args.cmd == "prepare":
        build_prompt(args.edit_dir.resolve(), args.max_speakers, args.silence)
    elif args.cmd == "apply":
        apply_labels(args.edit_dir.resolve(), args.stem, args.labels.resolve())


if __name__ == "__main__":
    main()
