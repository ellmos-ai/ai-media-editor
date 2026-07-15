from __future__ import annotations

import json
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT, ROOT / "stt", ROOT / "tools"):
    sys.path.insert(0, str(directory))

import cut_view  # noqa: E402
import diarize_llm  # noqa: E402
import editor  # noqa: E402
import frame_view  # noqa: E402
import mac_remote  # noqa: E402
import scribe_schema  # noqa: E402
import transcribe_local  # noqa: E402


def completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


class ScribeSchemaTests(unittest.TestCase):
    def test_builds_spacing_between_nonempty_words(self) -> None:
        words = [
            scribe_schema.Word(" first ", 0.0, 0.2),
            scribe_schema.Word("   ", 0.3, 0.4),
            scribe_schema.Word("second", 0.8, 1.0),
        ]
        payload = scribe_schema.build_scribe_payload(words)
        self.assertEqual([item["type"] for item in payload["words"]], ["word", "spacing", "word"])
        self.assertEqual(payload["words"][1]["start"], 0.2)
        self.assertEqual(payload["words"][1]["end"], 0.8)

    def test_rejects_unsorted_words(self) -> None:
        words = [scribe_schema.Word("later", 2, 3), scribe_schema.Word("earlier", 1, 2)]
        with self.assertRaisesRegex(ValueError, "chronologisch"):
            scribe_schema.build_scribe_payload(words)

    def test_rejects_invalid_time_range(self) -> None:
        with self.assertRaisesRegex(ValueError, "Zeitbereich"):
            scribe_schema.build_scribe_payload([scribe_schema.Word("bad", 2, 1)])

    def test_rejects_empty_speaker(self) -> None:
        with self.assertRaisesRegex(ValueError, "speaker_id"):
            scribe_schema.build_scribe_payload([scribe_schema.Word("bad", 0, 1, "")])


class TranscriptCacheTests(unittest.TestCase):
    def _valid_cache(self, root: Path) -> tuple[Path, Path, Path]:
        media = root / "sample.wav"
        media.write_bytes(b"audio-v1")
        transcript = root / "sample.json"
        transcript.write_text(
            json.dumps({"language_code": "de", "text": "hi", "words": [
                {"type": "word", "text": "hi", "start": 0.0, "end": 0.2, "speaker_id": "speaker_0"}
            ]}),
            encoding="utf-8",
        )
        metadata = transcript.with_suffix(".meta")
        signature = transcribe_local.cache_signature(media, "faster", "medium", "de", "auto", None, None)
        metadata.write_text(json.dumps(signature), encoding="utf-8")
        return media, transcript, metadata

    def test_cache_validates_source_and_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            media, transcript, _ = self._valid_cache(Path(tmp))
            self.assertTrue(transcribe_local.cache_is_valid(
                media, transcript, "faster", "medium", "de", "auto", None, None
            ))
            self.assertFalse(transcribe_local.cache_is_valid(
                media, transcript, "whisperx", "large-v3", "de", "auto", 2, "token"
            ))

    def test_cache_invalidates_when_source_bytes_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            media, transcript, _ = self._valid_cache(Path(tmp))
            media.write_bytes(b"audio-v2")
            self.assertFalse(transcribe_local.cache_is_valid(
                media, transcript, "faster", "medium", "de", "auto", None, None
            ))

    def test_cache_rejects_malformed_transcript(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            media, transcript, _ = self._valid_cache(Path(tmp))
            transcript.write_text("not-json", encoding="utf-8")
            self.assertFalse(transcribe_local.cache_is_valid(
                media, transcript, "faster", "medium", "de", "auto", None, None
            ))

    def test_cache_rejects_non_numeric_word_times(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            media, transcript, _ = self._valid_cache(Path(tmp))
            payload = json.loads(transcript.read_text(encoding="utf-8"))
            payload["words"][0]["start"] = "zero"
            transcript.write_text(json.dumps(payload), encoding="utf-8")
            self.assertFalse(transcribe_local.cache_is_valid(
                media, transcript, "faster", "medium", "de", "auto", None, None
            ))

    def test_cache_rejects_malformed_spacing_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            media, transcript, _ = self._valid_cache(Path(tmp))
            payload = json.loads(transcript.read_text(encoding="utf-8"))
            payload["words"].append({"type": "spacing", "text": " ", "start": "bad", "end": 0.3})
            transcript.write_text(json.dumps(payload), encoding="utf-8")
            self.assertFalse(transcribe_local.cache_is_valid(
                media, transcript, "faster", "medium", "de", "auto", None, None
            ))

    def test_transcribe_one_reuses_only_valid_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            media, transcript, metadata = self._valid_cache(root)
            edit = root / "edit"
            target_dir = edit / "transcripts"
            target_dir.mkdir(parents=True)
            transcript.replace(target_dir / transcript.name)
            metadata.replace(target_dir / metadata.name)
            with mock.patch.object(transcribe_local, "extract_audio", side_effect=AssertionError("must not run")):
                result = transcribe_local.transcribe_one(media, edit, verbose=False)
            self.assertEqual(result, target_dir / "sample.json")

    def test_transcribe_one_writes_payload_and_metadata_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            media = root / "sample.wav"
            media.write_bytes(b"audio")
            edit = root / "edit"
            transcripts = edit / "transcripts"
            transcripts.mkdir(parents=True)
            fixed_temp = transcripts / "sample.json.tmp"
            fixed_temp.write_text("belongs to another writer", encoding="utf-8")

            def fake_extract(_media: Path, destination: Path) -> None:
                destination.write_bytes(b"wav")

            with (
                mock.patch.object(transcribe_local, "extract_audio", side_effect=fake_extract),
                mock.patch.object(
                    transcribe_local,
                    "transcribe_faster_whisper",
                    return_value=([scribe_schema.Word("hi", 0, 0.2)], "de"),
                ),
            ):
                result = transcribe_local.transcribe_one(media, edit, verbose=False)
            self.assertTrue(result.is_file())
            self.assertTrue(result.with_suffix(".meta").is_file())
            self.assertEqual(fixed_temp.read_text(encoding="utf-8"), "belongs to another writer")
            self.assertEqual(list(result.parent.glob(".*.tmp")), [])

    def test_transcribe_one_rejects_unknown_engine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "sample.wav"
            media.write_bytes(b"audio")
            with self.assertRaisesRegex(ValueError, "Unbekannte"):
                transcribe_local.transcribe_one(media, Path(tmp) / "edit", engine="typo", verbose=False)


class EditorTests(unittest.TestCase):
    def test_project_names_cannot_escape_projects(self) -> None:
        for name in ("..", "../outside", "C:\\outside", "bad/name"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                editor._project_dir(name)
        self.assertEqual(editor._project_dir("Mein Projekt").name, "Mein Projekt")

    def test_project_media_refreshes_when_source_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.wav"
            destination = root / "project.wav"
            fixed_temp = root / "project.wav.tmp"
            fixed_temp.write_bytes(b"belongs to another writer")
            source.write_bytes(b"one")
            editor._sync_project_media(source, destination)
            self.assertEqual(destination.read_bytes(), b"one")
            source.write_bytes(b"two")
            editor._sync_project_media(source, destination)
            self.assertEqual(destination.read_bytes(), b"two")
            self.assertEqual(fixed_temp.read_bytes(), b"belongs to another writer")

    def test_resolve_engine_rejects_configuration_typo(self) -> None:
        cfg = {"engines": {"single_speaker": "unknown", "multi_speaker": "faster"}}
        with self.assertRaisesRegex(ValueError, "Unbekannte"):
            editor.resolve_engine(editor.USECASES[1], None, cfg)

    def test_doctor_reports_missing_venv_without_crashing(self) -> None:
        cfg = {
            "compute": {"prefer": "local"},
            "mac": {},
            "engines": {"multi_speaker": "faster"},
            "paths": {"venv_python": "Z:/missing/python.exe", "video_use": "Z:/missing/video-use"},
            "hf_token": "",
        }

        def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            if command[0] == "ffmpeg":
                return completed()
            if command[0] == "node":
                return completed(stdout="v22.0.0")
            raise AssertionError(f"unexpected command: {command}")

        with (
            mock.patch.object(editor, "load_config", return_value=cfg),
            mock.patch.object(editor.subprocess, "run", side_effect=fake_run),
            mock.patch.object(editor.mac_remote, "is_reachable") as remote_probe,
        ):
            self.assertEqual(editor.doctor(), 1)
            remote_probe.assert_not_called()

    def test_helper_failure_is_non_success(self) -> None:
        with mock.patch.object(editor.subprocess, "run", return_value=completed(3, stderr="boom")):
            self.assertIsNone(editor._run_helper(["helper"], "test helper"))

    def test_prepare_does_not_accept_stale_helper_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            media = root / "input.wav"
            media.write_bytes(b"audio")
            edit = root / "projects" / "demo" / "edit"
            edit.mkdir(parents=True)
            (edit / "takes_packed.md").write_text("stale", encoding="utf-8")
            (edit / "cut_view.md").write_text("stale", encoding="utf-8")
            cfg = {
                "compute": {"prefer": "local"},
                "mac": {},
                "engines": {"single_speaker": "faster", "multi_speaker": "faster"},
                "models": {"faster_local": "medium"},
                "paths": {"venv_python": "python", "video_use": str(root / "video-use")},
                "language": "de",
                "hf_token": "",
            }
            with (
                mock.patch.object(editor, "HERE", root),
                mock.patch.object(editor, "load_config", return_value=cfg),
                mock.patch.object(editor.transcribe_local, "cache_is_valid", return_value=True),
                mock.patch.object(editor, "_run_helper", return_value=completed()),
            ):
                self.assertEqual(editor.prepare(media, 1, "demo", None), 1)
            self.assertFalse((edit / "takes_packed.md").exists())
            self.assertFalse((edit / "cut_view.md").exists())

    def test_external_frame_project_name_cannot_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"
            video.write_bytes(b"video")
            with self.assertRaises(ValueError):
                editor._resolve_video(str(video), "../outside")


class FrameViewTests(unittest.TestCase):
    def test_timestamp_generation_caps_early(self) -> None:
        stamps, capped = frame_view.gen_timestamps(0, 1_000_000, 0.001, 3)
        self.assertEqual(stamps, [0.0, 0.001, 0.002])
        self.assertTrue(capped)

    def test_timestamp_generation_rejects_nonpositive_step(self) -> None:
        for step in (0, -1):
            with self.subTest(step=step), self.assertRaises(ValueError):
                frame_view.gen_timestamps(0, 10, step, 60)

    def test_failed_extract_does_not_reuse_stale_frame(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "frame.jpg"
            out.write_bytes(b"stale")
            with mock.patch.object(frame_view.subprocess, "run", return_value=completed(1)):
                self.assertFalse(frame_view.extract_frame(Path("video.mp4"), 0, out, 640, None, False))
            self.assertFalse(out.exists())

    def test_failed_sheet_does_not_reuse_stale_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            frames = Path(tmp)
            stale = frames / "sheet_001.jpg"
            stale.write_bytes(b"stale")
            with mock.patch.object(frame_view.subprocess, "run", return_value=completed(1)):
                self.assertEqual(frame_view.contact_sheet(Path("video.mp4"), frames, 10, 4, 4, 640, None), [])
            self.assertFalse(stale.exists())

    def test_run_requires_both_zoom_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"
            video.write_bytes(b"video")
            with self.assertRaisesRegex(ValueError, "gemeinsam"):
                frame_view.run(video, Path(tmp) / "edit", 10, 1, None, None, False, 4, 4, 640, 60, None)

    def test_run_returns_failure_when_no_frames_are_created(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"
            video.write_bytes(b"video")
            with (
                mock.patch.object(frame_view, "ffprobe_duration", return_value=5),
                mock.patch.object(frame_view, "sample_frames", return_value=([], 0)),
            ):
                with redirect_stdout(io.StringIO()):
                    result = frame_view.run(video, Path(tmp) / "edit", 10, None, None, None,
                                            False, 4, 4, 640, 60, None)
            self.assertEqual(result, 1)
            self.assertFalse((Path(tmp) / "edit" / "frame_view.md").exists())


class DiarizationTests(unittest.TestCase):
    PHRASES = [
        {"i": 0, "start": 0.0, "end": 0.006, "text": "A"},
        {"i": 1, "start": 0.006, "end": 1.0, "text": "B"},
    ]

    def test_label_map_requires_exact_coverage(self) -> None:
        with self.assertRaisesRegex(ValueError, "unvollständig"):
            diarize_llm.parse_label_map(self.PHRASES, [{"i": 0, "speaker": 0}])

    def test_label_map_rejects_fractional_and_negative_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "Ganzzahlen"):
            diarize_llm.parse_label_map(self.PHRASES, {"0": 0, "1": 1.5})
        with self.assertRaisesRegex(ValueError, "0 oder größer"):
            diarize_llm.parse_label_map(self.PHRASES, {"0": 0, "1": -1})

    def test_label_map_honors_persisted_speaker_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "Grenze"):
            diarize_llm.parse_label_map(
                self.PHRASES, {"0": 0, "1": 999}, max_speakers=2
            )

    def test_prompt_keeps_full_timing_precision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            edit = Path(tmp)
            transcripts = edit / "transcripts"
            transcripts.mkdir()
            payload = {"words": [
                {"type": "word", "text": "A.", "start": 0.006, "end": 0.123, "speaker_id": "speaker_0"}
            ]}
            (transcripts / "clip.json").write_text(json.dumps(payload), encoding="utf-8")
            diarize_llm.build_prompt(edit, max_speakers=2)
            phrases = json.loads((edit / "diarization" / "clip.phrases.json").read_text(encoding="utf-8"))
            self.assertEqual(phrases[0]["start"], 0.006)
            self.assertEqual(phrases[0]["end"], 0.123)
            metadata = json.loads((edit / "diarization" / "clip.meta.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["max_speakers"], 2)

    def test_apply_uses_latest_segment_at_shared_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            edit = Path(tmp)
            (edit / "diarization").mkdir()
            (edit / "transcripts").mkdir()
            (edit / "diarization" / "clip.phrases.json").write_text(json.dumps(self.PHRASES), encoding="utf-8")
            labels = edit / "labels.json"
            labels.write_text(json.dumps({"0": 0, "1": 1}), encoding="utf-8")
            transcript = edit / "transcripts" / "clip.json"
            transcript.write_text(json.dumps({"words": [
                {"type": "word", "text": "B", "start": 0.006, "end": 0.2, "speaker_id": "speaker_0"}
            ]}), encoding="utf-8")

            def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
                (edit / "takes_packed.md").write_text("ok", encoding="utf-8")
                return completed()

            with (
                mock.patch.object(diarize_llm, "_packer_command", return_value=["python", "pack.py"]),
                mock.patch.object(diarize_llm.subprocess, "run", side_effect=fake_run),
            ):
                diarize_llm.apply_labels(edit, "clip", labels)
            data = json.loads(transcript.read_text(encoding="utf-8"))
            self.assertEqual(data["words"][0]["speaker_id"], "speaker_1")

    def test_apply_restores_transcript_when_repack_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            edit = Path(tmp)
            (edit / "diarization").mkdir()
            (edit / "transcripts").mkdir()
            phrases = [self.PHRASES[0]]
            (edit / "diarization" / "clip.phrases.json").write_text(json.dumps(phrases), encoding="utf-8")
            labels = edit / "labels.json"
            labels.write_text(json.dumps({"0": 1}), encoding="utf-8")
            transcript = edit / "transcripts" / "clip.json"
            original = json.dumps({"words": [
                {"type": "word", "text": "A", "start": 0.0, "end": 0.006, "speaker_id": "speaker_0"}
            ]})
            transcript.write_text(original, encoding="utf-8")
            takes = edit / "takes_packed.md"
            takes.write_text("old takes", encoding="utf-8")
            with (
                mock.patch.object(diarize_llm, "_packer_command", return_value=["python", "pack.py"]),
                mock.patch.object(diarize_llm.subprocess, "run", return_value=completed(2, stderr="failed")),
                self.assertRaisesRegex(RuntimeError, "wiederhergestellt"),
            ):
                diarize_llm.apply_labels(edit, "clip", labels)
            self.assertEqual(transcript.read_text(encoding="utf-8"), original)
            self.assertEqual(takes.read_text(encoding="utf-8"), "old takes")

    def test_stem_cannot_escape_transcript_directory(self) -> None:
        with self.assertRaises(ValueError):
            diarize_llm._safe_stem("../outside")


class RemoteRoutingTests(unittest.TestCase):
    CFG = {
        "host": "media.example",
        "user": "worker",
        "ssh_key": "key",
        "connect_timeout": 1,
        "workdir": "~/podcast work",
        "venv_activate": "source ~/.venvs/media/bin/activate",
    }

    def test_home_paths_are_shell_quoted(self) -> None:
        quoted = mac_remote.shq("~/podcast work/clip;touch PWN.mp4")
        self.assertEqual(quoted, '"$HOME"/\'podcast work/clip;touch PWN.mp4\'')

    def test_invalid_ssh_target_is_rejected(self) -> None:
        cfg = dict(self.CFG, user="-oProxyCommand")
        with self.assertRaises(ValueError):
            mac_remote._target(cfg)

    def test_ssh_run_converts_launch_error_to_fallback_tuple(self) -> None:
        with mock.patch.object(mac_remote.subprocess, "run", side_effect=FileNotFoundError("ssh")):
            rc, _out, err = mac_remote._ssh_run(self.CFG, "true")
        self.assertEqual(rc, -1)
        self.assertIn("ssh", err)

    def test_remote_failure_still_cleans_isolated_job(self) -> None:
        commands: list[str] = []

        def fake_ssh(_cfg: dict, command: str, timeout: int = 3600) -> tuple[int, str, str]:
            commands.append(command)
            return 0, "", ""

        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "clip.wav"
            media.write_bytes(b"audio")
            with (
                mock.patch.object(mac_remote, "is_reachable", return_value=True),
                mock.patch.object(mac_remote, "_ssh_run", side_effect=fake_ssh),
                mock.patch.object(mac_remote, "_scp", return_value=False),
            ):
                self.assertIsNone(mac_remote.run_remote(media, Path(tmp) / "edit", self.CFG, verbose=False))
        self.assertTrue(any(command.startswith("rm -rf") for command in commands))

    def test_remote_command_uses_token_file_and_quotes_media_name(self) -> None:
        commands: list[str] = []

        def fake_ssh(_cfg: dict, command: str, timeout: int = 3600) -> tuple[int, str, str]:
            commands.append(command)
            return 0, "", ""

        def fake_scp(_cfg: dict, source: str, destination: str) -> bool:
            target = Path(destination)
            if destination.endswith(".json.tmp"):
                target.write_text("{}", encoding="utf-8")
            elif destination.endswith(".meta.tmp"):
                target.write_text("{}", encoding="utf-8")
            return True

        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "clip;touch PWN.wav"
            media.write_bytes(b"audio")
            marker = "sensitive-marker"
            remote_options = {"hf_" + "token": marker}
            with (
                mock.patch.object(mac_remote, "is_reachable", return_value=True),
                mock.patch.object(mac_remote, "_ssh_run", side_effect=fake_ssh),
                mock.patch.object(mac_remote, "_scp", side_effect=fake_scp),
                mock.patch.object(mac_remote.transcribe_local, "cache_is_valid", return_value=True),
            ):
                result = mac_remote.run_remote(
                    media, Path(tmp) / "edit", self.CFG, verbose=False, **remote_options
                )
        self.assertIsNotNone(result)
        transcribe_commands = [command for command in commands if "transcribe_local.py" in command]
        self.assertEqual(len(transcribe_commands), 1)
        self.assertIn("--hf-token-file", transcribe_commands[0])
        self.assertNotIn(marker, transcribe_commands[0])
        self.assertIn("clip;touch PWN.wav'", transcribe_commands[0])
        self.assertTrue(any(command.startswith("umask 077; mkdir -p") and "chmod 700" in command
                            for command in commands))
        self.assertTrue(any(command.startswith("chmod 600") for command in commands))


class CutViewTests(unittest.TestCase):
    def test_find_pauses_tolerates_missing_end(self) -> None:
        pauses, words = cut_view.find_pauses([
            {"type": "word", "text": "a", "start": 0.0, "end": None},
            {"type": "word", "text": "b", "start": 1.0, "end": 1.2},
        ])
        self.assertEqual(len(words), 2)
        self.assertEqual(pauses[0]["dur"], 1.0)


if __name__ == "__main__":
    unittest.main()
