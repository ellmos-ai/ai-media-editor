# Changelog

## Unreleased

### Fixed
- Use real German umlauts in the user-facing use-case labels and next-step CLI output.

## [0.2.2] - 2026-07-27

### Changed
- Updated `llms.txt` verification timestamp to `2026-07-27` after discoverability, SEO, and test suite audit (38/38 unit tests passing).

## [0.2.1] - 2026-07-25

### Added
- Standard PEP 621 `pyproject.toml` package & test configuration.
- Shields.io status & quality badges (pytest, MIT license, Python version, LLM-ready) in `README.md`.
- GFM LLM / Agent native integration callout note (`> [!NOTE]`) in `README.md`.
- Mermaid System Architecture flow diagram in `README.md`.

### Changed
- Synchronized `llms.txt` verification timestamp and external discovery status to `2026-07-25`.

### Fixed

- Correct `ellmos-module.v2.json` visibility from `public-candidate` to `public`.
  The repository has been published for a while; the schema distinguishes the two
  values, so catalog and discovery tooling reading the manifest classified this
  module as not-yet-published.

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
