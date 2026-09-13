# Completed work: ai-media-editor

This file preserves demonstrably completed entries transferred from `TODO.md` by
the MAINTAINER on 2026-09-05. The direct predecessor is the tracked `TODO.md` at
Git commit `35072ca7a3bcaa7b9537f4fa1d2d2770a9aad29f`; its pre-transfer SHA-256 was
`CA6B7B74000B0E053B70BF3E2594D4C7629DD7CAEFA408C06A83EEF55505CDE6`.

Rollback: restore the checklist below beneath `## Completed safety and correctness
gates` in `TODO.md`, then remove this newly added file through a recoverable workflow.

## Completed safety and correctness gates

- [x] No secrets, real settings, project media, model caches, or local tool trees tracked.
- [x] Project and transcript stem inputs cannot escape their intended directories.
- [x] Remote shell arguments are quoted; jobs use isolated directories and best-effort cleanup.
- [x] Remote HF tokens are transferred by temporary file instead of process arguments.
- [x] Transcript caches bind to source SHA-256 and transcription configuration and are written atomically.
- [x] Failed pack/cut/re-pack helpers return failure instead of reporting incomplete success.
- [x] Frame parameters are bounded and failed ffmpeg runs cannot reuse stale frames/sheets.
- [x] LLM diarization preserves timestamp precision and requires exact, valid label coverage.
- [x] `doctor` reports a missing venv without crashing and treats remote compute as optional in local mode.
- [x] `SECURITY.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, CI, and a dependency-free regression suite exist.
- [x] Public production pointers use portable paths and explicit rights/consent/privacy upload gates.
