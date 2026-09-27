"""Scribe schema components — contract between local STT and video-use.

video-use expects ElevenLabs Scribe response structure in
<edit_dir>/transcripts/<name>.json. Two downstream consumers read it:

  * helpers/pack_transcripts.py  -> data["words"], each entry has
        type ∈ {"word", "spacing", "audio_event"} and fields
        text / start / end / speaker_id.
  * helpers/render.py::_words_in_range -> filters on type == "word" and
        uses start / end / text for the master SRT.

This module constructs a compatible Scribe JSON structure from generic Word triplets
(text, start, end, speaker).
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Word:
    """A recognized word with word-level timestamps (in seconds)."""
    text: str
    start: float
    end: float
    speaker: str = "speaker_0"


def build_scribe_payload(
    words: list[Word],
    language_code: str = "de",
    spacing_eps: float = 1e-3,
) -> dict:
    """Convert a list of words into a Scribe-compatible response payload.

    Inserts spacing entries between consecutive words to represent silence gaps,
    which serve as phrase boundary markers for pack_transcripts.py. render.py
    ignores spacing entries (filtering on type == "word").

    Args:
        words: Chronologically sorted words.
        language_code: ISO language code (Scribe field).
        spacing_eps: Minimum gap duration to generate a spacing entry.

    Returns:
        Dict in Scribe format: {"language_code", "text", "words": [...]}.
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
    """Scribe-style speaker ID: 0 -> 'speaker_0'."""
    return f"speaker_{index}"
