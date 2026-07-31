from __future__ import annotations

import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT, ROOT / "stt", ROOT / "tools"):
    sys.path.insert(0, str(directory))

try:
    import numpy as np  # noqa: E402

    import compose_music  # noqa: E402

    HAVE_NUMPY = True
except ImportError:  # numpy is an optional dependency of the fast gate
    HAVE_NUMPY = False


@unittest.skipUnless(HAVE_NUMPY, "numpy nicht installiert")
class ComposeMusicTests(unittest.TestCase):
    STORYLINE = {
        "title": "smoke",
        "duration": 3.0,
        "bpm": 120,
        "key": "C",
        "mode": "minor",
        "style": "chiptune",
        "seed": 7,
        "sections": [
            {"start": 0.0, "end": 1.5, "emotion": "calm", "intensity": 0.2},
            {"start": 1.5, "end": 3.0, "emotion": "driving", "intensity": 0.8},
        ],
        "events": [{"type": "damp", "time": 0.75, "depth": 0.5, "width": 0.2}],
    }

    def _render(self, tmp: Path) -> dict:
        return compose_music.compose(self.STORYLINE, tmp / "score",
                                     write_mp3=False, verbose=False)

    def test_three_second_render_produces_valid_wav(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self._render(Path(tmp))
            with wave.open(str(result["wav"]), "rb") as w:
                self.assertEqual(w.getnchannels(), 2)
                self.assertEqual(w.getsampwidth(), 2)
                self.assertEqual(w.getframerate(), compose_music.SAMPLE_RATE)
                frames = w.readframes(w.getnframes())
            self.assertEqual(w.getnframes(), int(3.0 * compose_music.SAMPLE_RATE))
            samples = np.frombuffer(frames, dtype=np.int16)
            self.assertGreater(int(np.max(np.abs(samples))), 100)

    def test_arrangement_log_records_sections_and_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self._render(Path(tmp))
            payload = json.loads(result["notes"].read_text(encoding="utf-8"))
            self.assertEqual(len(payload["sections"]), 2)
            self.assertEqual(payload["events"]["damps"][0]["time"], 0.75)
            self.assertGreater(len(payload["notes"]), 0)
            layers = {note["layer"] for note in payload["notes"]}
            self.assertIn("pad", layers)

    def test_render_is_deterministic_for_same_seed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = compose_music.compose(self.STORYLINE, Path(tmp) / "a",
                                          write_mp3=False, verbose=False)
            second = compose_music.compose(self.STORYLINE, Path(tmp) / "b",
                                           write_mp3=False, verbose=False)
            self.assertEqual(first["wav"].read_bytes(), second["wav"].read_bytes())

    def test_midi_export_is_valid_smf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self._render(Path(tmp))
            data = result["midi"].read_bytes()
            self.assertTrue(data.startswith(b"MThd"))
            self.assertEqual(data.count(b"MTrk"), 2)  # tempo track + note track
            self.assertIn(b"\xff\x51\x03", data)  # tempo meta event
            stats = compose_music.write_midi(
                Path(tmp) / "x.mid",
                json.loads(result["notes"].read_text(encoding="utf-8"))["notes"],
                result["config"]["sections"], "chiptune", 120)
            self.assertGreater(stats["note_events"], 0)
            self.assertEqual(stats["tempo_events"], 2)

    def test_midi_program_map_covers_all_styles(self) -> None:
        for style in compose_music.STYLES:
            self.assertEqual(set(compose_music.GM_PROGRAMS[style]),
                             set(compose_music.LAYER_CHANNELS))

    def test_invalid_storyline_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = dict(self.STORYLINE, sections=[
                {"start": 0.0, "end": 2.0, "emotion": "typo"},
            ])
            with self.assertRaisesRegex(ValueError, "Emotion"):
                compose_music.compose(bad, Path(tmp) / "x", verbose=False)


if __name__ == "__main__":
    unittest.main()
