"""Scribe-Schema-Bausteine — der Vertrag zwischen unserem lokalen STT und video-use.

video-use erwartet die ElevenLabs-Scribe-Response-Struktur in
<edit_dir>/transcripts/<name>.json. Zwei Downstream-Konsumenten lesen sie:

  * helpers/pack_transcripts.py  -> data["words"], jeder Eintrag hat
        type ∈ {"word", "spacing", "audio_event"} und Felder
        text / start / end / speaker_id. Phrasen brechen bei spacing-Gap
        >= 0.5s ODER Sprecherwechsel ODER Wort-zu-Wort-Gap >= 0.5s.
  * helpers/render.py::_words_in_range -> filtert auf type == "word" und
        nutzt start / end / text fuer die Master-SRT.

Dieses Modul baut aus generischen Wort-Tripeln (text, start, end, speaker)
ein für diese Konsumenten kompatibles Scribe-JSON. So muss an video-use selbst NICHTS
gepatcht werden — wir schreiben nur dieselbe Datei, die sonst ElevenLabs
schreiben wuerde. Quelle der Wahrheit fuer das Format: die beiden Helfer oben.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Word:
    """Ein erkanntes Wort mit Wort-Zeitstempeln (Sekunden)."""
    text: str
    start: float
    end: float
    speaker: str = "speaker_0"


def build_scribe_payload(
    words: list[Word],
    language_code: str = "de",
    spacing_eps: float = 1e-3,
) -> dict:
    """Wandelt eine Wortliste in eine Scribe-kompatible Response um.

    Zwischen zwei aufeinanderfolgenden Woertern wird ein 'spacing'-Eintrag
    eingefuegt, der genau den zeitlichen Abstand (Stille) abbildet — das ist
    das Signal, an dem pack_transcripts.py Phrasen schneidet. render.py
    ignoriert spacing-Eintraege (filtert auf type == "word"), daher bleibt
    die SRT-Erzeugung unberuehrt.

    Args:
        words: chronologisch sortierte Woerter.
        language_code: ISO-Sprachcode (Scribe-Feld).
        spacing_eps: Mindestabstand, ab dem ein spacing-Eintrag erzeugt wird.

    Returns:
        dict im Scribe-Format: {"language_code", "text", "words": [...]}.
    """
    if not math.isfinite(spacing_eps) or spacing_eps < 0:
        raise ValueError("spacing_eps muss eine endliche Zahl >= 0 sein.")
    normalized: list[tuple[str, float, float, str]] = []
    previous_start = -1.0
    for word in words:
        clean = word.text.strip()
        if not clean:
            continue
        start = float(word.start)
        end = float(word.end)
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end < start:
            raise ValueError(f"Ungültiger Wort-Zeitbereich: {word!r}")
        if start < previous_start:
            raise ValueError("Wörter müssen chronologisch nach Startzeit sortiert sein.")
        speaker = str(word.speaker).strip()
        if not speaker:
            raise ValueError("speaker_id darf nicht leer sein.")
        normalized.append((clean, start, end, speaker))
        previous_start = start

    out_words: list[dict] = []
    text_parts: list[str] = []

    for i, (clean, start, end, speaker) in enumerate(normalized):
        out_words.append({
            "type": "word",
            "text": clean,
            "start": round(start, 3),
            "end": round(end, 3),
            "speaker_id": speaker,
        })
        text_parts.append(clean)

        # Spacing-Eintrag zum naechsten Wort (Stille-/Pausen-Signal)
        if i + 1 < len(normalized):
            _, gap_end, _, _ = normalized[i + 1]
            gap_start = end
            if gap_end - gap_start > spacing_eps:
                out_words.append({
                    "type": "spacing",
                    "text": " ",
                    "start": round(gap_start, 3),
                    "end": round(gap_end, 3),
                    "speaker_id": speaker,
                })

    return {
        "language_code": language_code,
        "text": " ".join(text_parts),
        "words": out_words,
    }


def speaker_label(index: int) -> str:
    """Scribe-Stil-Sprecher-ID: 0 -> 'speaker_0'. pack_transcripts kuerzt zu 'S0'."""
    return f"speaker_{index}"
