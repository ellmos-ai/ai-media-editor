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
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# pack_transcripts (Re-Pack) aus video-use wiederverwenden
def _packer_command(edit_dir: Path) -> list[str]:
    try:
        cfg = json.loads((Path(__file__).resolve().parent.parent / "config" / "settings.json").read_text(encoding="utf-8"))
        vu_root = Path(cfg["paths"]["video_use"])
        python = str(cfg["paths"]["venv_python"])
    except (OSError, KeyError, json.JSONDecodeError):
        vu_root = os.environ.get("VIDEO_USE_DIR")
        if not vu_root:
            raise RuntimeError(
                "video-use-Pfad nicht konfiguriert: paths.video_use in config/settings.json "
                "setzen (siehe settings.example.json) oder Umgebungsvariable VIDEO_USE_DIR."
            )
        vu_root = Path(vu_root)
        python = sys.executable
    pack = vu_root / "helpers" / "pack_transcripts.py"
    if not pack.is_file():
        raise RuntimeError(f"pack_transcripts.py nicht gefunden: {pack}")
    return [python, str(pack), "--edit-dir", str(edit_dir)]


_SENT_END = (".", "?", "!", "…")


def _safe_stem(stem: str) -> str:
    if not stem or stem in {".", ".."} or Path(stem).name != stem:
        raise ValueError("--stem muss ein einzelner Dateistamm sein.")
    if any(char in stem for char in '<>:"/\\|?*'):
        raise ValueError("--stem enthält ein unzulässiges Zeichen.")
    return stem


def _exact_int(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("Label-Indizes und Sprecher müssen Ganzzahlen sein.")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.lstrip("-").isdigit():
        return int(value)
    raise ValueError("Label-Indizes und Sprecher müssen Ganzzahlen sein.")


def _write_text_atomic(path: Path, content: str) -> None:
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


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
    if max_speakers is not None and max_speakers < 1:
        raise ValueError("max_speakers muss mindestens 1 sein.")
    if silence <= 0:
        raise ValueError("silence muss größer als 0 sein.")
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
            {"i": i, "start": float(p["start"]), "end": float(p["end"]), "text": p["text"]}
            for i, p in enumerate(phrases)
        ]
        phrases_path = out_dir / f"{jf.stem}.phrases.json"
        _write_text_atomic(phrases_path, json.dumps(items, indent=2, ensure_ascii=False))

        metadata_path = out_dir / f"{jf.stem}.meta.json"
        _write_text_atomic(
            metadata_path,
            json.dumps({"max_speakers": max_speakers}, indent=2, ensure_ascii=False),
        )

        spk_hint = (f"Verwende höchstens {max_speakers} Sprecher." if max_speakers
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
        _write_text_atomic(prompt_path, prompt)
        written.append(prompt_path)
        print(f"  Diarisierungs-Prompt: {prompt_path}  ({len(items)} Phrasen)")
    return written


def parse_label_map(
    phrases: list[dict], raw_labels: object, max_speakers: int | None = None
) -> dict[int, int]:
    """Validate an exact phrase-to-speaker assignment without silent defaults."""
    if max_speakers is not None and max_speakers < 1:
        raise ValueError("max_speakers muss mindestens 1 sein.")
    expected: set[int] = set()
    for phrase in phrases:
        if not isinstance(phrase, dict) or not all(key in phrase for key in ("i", "start", "end")):
            raise ValueError("Jede Phrase braucht i, start und end.")
        index = _exact_int(phrase["i"])
        start, end = float(phrase["start"]), float(phrase["end"])
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end < start:
            raise ValueError(f"Phrase {index} hat einen ungültigen Zeitbereich.")
        expected.add(index)
    if len(expected) != len(phrases):
        raise ValueError("Phrasen enthalten doppelte Indizes.")

    items: list[tuple[object, object]]
    if isinstance(raw_labels, dict):
        items = list(raw_labels.items())
    elif isinstance(raw_labels, list):
        items = []
        for entry in raw_labels:
            if not isinstance(entry, dict) or "i" not in entry or "speaker" not in entry:
                raise ValueError("Jedes Label braucht die Felder 'i' und 'speaker'.")
            items.append((entry["i"], entry["speaker"]))
    else:
        raise ValueError("Labels müssen ein JSON-Objekt oder eine JSON-Liste sein.")

    result: dict[int, int] = {}
    for raw_index, raw_speaker in items:
        index = _exact_int(raw_index)
        speaker = _exact_int(raw_speaker)
        if index in result:
            raise ValueError(f"Doppeltes Label für Phrase {index}.")
        if speaker < 0:
            raise ValueError("Sprecher-IDs müssen 0 oder größer sein.")
        if max_speakers is not None and speaker >= max_speakers:
            raise ValueError(
                f"Sprecher-ID {speaker} überschreitet die Grenze von {max_speakers} Sprechern."
            )
        result[index] = speaker

    missing = sorted(expected - result.keys())
    extra = sorted(result.keys() - expected)
    if missing or extra:
        raise ValueError(f"Labels sind unvollständig (fehlend={missing}, unbekannt={extra}).")
    return result


def apply_labels(edit_dir: Path, stem: str, labels_path: Path) -> Path:
    """Schreibt Sprecher zeitbasiert ins Scribe-JSON zurück und re-packt."""
    stem = _safe_stem(stem)
    out_dir = edit_dir / "diarization"
    phrases = json.loads((out_dir / f"{stem}.phrases.json").read_text(encoding="utf-8"))
    raw_labels = json.loads(Path(labels_path).read_text(encoding="utf-8"))
    metadata_path = out_dir / f"{stem}.meta.json"
    max_speakers = None
    if metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not isinstance(metadata, dict):
            raise ValueError("Diarisierungs-Metadaten müssen ein JSON-Objekt sein.")
        max_speakers = metadata.get("max_speakers")
        if max_speakers is not None:
            max_speakers = _exact_int(max_speakers)
    label_map = parse_label_map(phrases, raw_labels, max_speakers=max_speakers)

    # Zeit-Segmente bauen: (start, end, speaker_id)
    segments: list[tuple[float, float, str]] = []
    for p in phrases:
        spk = label_map[int(p["i"])]
        segments.append((float(p["start"]), float(p["end"]), f"speaker_{spk}"))

    def speaker_at(t: float) -> str | None:
        matches = [(s, spk) for s, e, spk in segments if s - 1e-6 <= t <= e + 1e-6]
        return max(matches, default=(0.0, None), key=lambda item: item[0])[1]

    jf = edit_dir / "transcripts" / f"{stem}.json"
    original = jf.read_text(encoding="utf-8")
    data = json.loads(original)
    last = "speaker_0"
    changed = 0
    for w in data.get("words", []):
        if w.get("type") != "word":
            w["speaker_id"] = last
            continue
        t = w.get("start")
        if t is None:
            raise ValueError("Wort ohne Startzeit kann keiner Phrase zugeordnet werden.")
        spk = speaker_at(float(t))
        if spk is None:
            raise ValueError(f"Wort bei {t}s liegt außerhalb aller Diarisierungsphrasen.")
        if w.get("speaker_id") != spk:
            changed += 1
        w["speaker_id"] = spk
        last = spk
    _write_text_atomic(jf, json.dumps(data, indent=2, ensure_ascii=False))

    n_spk = len({s for _, _, s in segments})

    # Re-Pack. Preserve and restore prior derived output if the downstream contract fails.
    takes = edit_dir / "takes_packed.md"
    previous_takes = takes.read_bytes() if takes.is_file() else None
    takes.unlink(missing_ok=True)

    def restore() -> None:
        _write_text_atomic(jf, original)
        if previous_takes is None:
            takes.unlink(missing_ok=True)
        else:
            fd, takes_tmp_name = tempfile.mkstemp(
                prefix=f".{takes.name}.", suffix=".tmp", dir=takes.parent
            )
            os.close(fd)
            takes_tmp = Path(takes_tmp_name)
            try:
                takes_tmp.write_bytes(previous_takes)
                os.replace(takes_tmp, takes)
            finally:
                takes_tmp.unlink(missing_ok=True)

    try:
        result = subprocess.run(_packer_command(edit_dir), capture_output=True, text=True)
    except (OSError, RuntimeError) as exc:
        restore()
        raise RuntimeError(f"Re-Pack fehlgeschlagen; Transkript wiederhergestellt: {exc}") from exc
    if result.returncode != 0:
        restore()
        detail = (result.stderr or result.stdout).strip()[-500:]
        raise RuntimeError(
            f"Re-Pack fehlgeschlagen (Exit {result.returncode}); Transkript wiederhergestellt: {detail}"
        )
    if not takes.is_file() or takes.stat().st_size == 0:
        restore()
        raise RuntimeError("Re-Pack meldete Erfolg, erzeugte aber keine takes_packed.md; Transkript wiederhergestellt.")
    print(f"  Sprecher angewendet: {n_spk} Sprecher, {changed} Wörter umgelabelt -> {jf.name}")
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
