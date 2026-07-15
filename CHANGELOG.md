# Changelog

## Unreleased

### Added

- Add 38 dependency-free regression tests plus GitHub Actions checks for Python
  3.11/3.12, Ruff, unit tests, and the `modes` CLI smoke.
- Add `SECURITY.md`, `CONTRIBUTING.md`, a pinned development-tool requirement,
  and `ellmos-module.v2.json` metadata.
- Add optional `production/` guides for music, podcast TTS, generative video,
  and portable pointers to text, story, and PR skills.
- Add `llms.txt` with crawler-friendly discovery and disambiguation context.

### Changed

- Bind transcript caches to source SHA-256 plus engine/model/language/device/
  speaker configuration; validate cached JSON and write transcript/metadata atomically.
- Isolate remote transcription jobs, quote remote paths and arguments, transfer
  HF tokens through a temporary file, validate downloads, and clean remote jobs
  on every exit path.
- Make pack, cut-view, and diarization re-pack failures return non-success and
  reject incomplete speaker-label assignments.
- Validate project/stem containment and frame parameters; prevent failed ffmpeg
  runs from reusing stale images.
- Align README, agent guide, use cases, settings, TODO, and production docs with
  the local-by-default engine/compute contract and explicit privacy/rights gates.
- Improve README start guidance and repository discovery context.

## 2026-06-17

- Initial public pre-release state for the local-first AI media editor workflow.
