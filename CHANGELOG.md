# Changelog

## [0.2.3] - 2026-09-20

### Added
- Upgraded bilingual documentation landing pages (`README.md` and `README_de.md`) to full 18-point quick navigation with 100% mutual reciprocal HTML anchor parity (`<a id="..."></a>`).
- Expanded comparative matrix to 10 feature dimensions mapped across all 10 governance runtime invariants (`INV-LOCAL-01` through `INV-SLA-10`) comparing `ai-media-editor` against Cloud SaaS (Descript / ElevenLabs), Heavy Commercial NLEs (Premiere / DaVinci), Raw CLI / Shell Scripts (FFmpeg), and Hosted Speech-to-Text APIs (Whisper API / Google STT).
- Formalized 4 target personas with distinct taxonomy (`[PERSONA-01]` through `[PERSONA-04]`), pain points, workflow solutions, and high-intent discovery search queries in `README.md`, `README_de.md`, and `MARKETING-LOG.txt`.
- Added Section 17 (Level 1 SBOM & Third-Party Licenses) and Section 18 (Statutory Notice & Liability Limitation under § 521 BGB Gefälligkeitsrecht) to both English and German documentation.
- Integrated Level 1 SBOM Invariant Cross-Reference Matrix table and explicit `RunAsInvoker` Non-Elevation Certification in `THIRD_PARTY_LICENSES.md`.
- Expanded automated contract test suite in `tests/test_metadata.py`:
  - `test_readme_18_point_quick_navigation_and_anchor_parity`: validates complete 18-point navigation and reciprocal anchor resolution across English and German READMEs.
  - `test_comparative_matrix_10_dimensions_and_invariants`: ensures all 10 governance invariants (`INV-LOCAL-01` to `INV-SLA-10`) and 4 alternatives are evaluated.
  - `test_statutory_bgb_disclaimer_parity`: verifies § 521 BGB statutory liability limitation in both `README.md` and `README_de.md`.
  - `test_level1_sbom_inventory_and_runasinvoker`: checks Level 1 SBOM table, Stand 2026-09-20, and `RunAsInvoker` certification in `THIRD_PARTY_LICENSES.md`.
  - `test_changelog_release_0_2_3`: validates release notes integrity for the 0.2.3 Pfad B discoverability and visual architecture overhaul.

### Changed
- Standardized `pyproject.toml` package metadata with `version = "0.2.3"` and `license-files = ["LICENSE", "THIRD_PARTY_LICENSES.md"]`.
- Bumped version to `0.2.3` across `VERSION`, `pyproject.toml`, `ellmos-module.v2.json`, `README.md`, `README_de.md`, and `llms.txt`.
- Synchronized Shields.io badges in `README.md` and `README_de.md` for version 0.2.3, verification timestamp `2026--09--20`, and updated passing contract test counts.
- Updated `llms.txt` verification timestamp to `2026-09-20` with 18-point navigation, 10-dimension matrix, and § 521 BGB statutory notice.

## [0.2.2] - 2026-09-12

### Added
- Standardized stale issues and pull requests lifecycle workflow in `.github/workflows/stale.yml` (`actions/stale@v9`) with 30-day inactivity detection, 7-day grace period, and priority label exemptions.
- Standardized `[project.optional-dependencies]` in `pyproject.toml` with `test` and `dev` tooling groups (`pytest>=8.0.0`, `pytest-asyncio>=0.23.0`, `ruff>=0.5.0`).
- Expanded automated contract test suite in `tests/test_metadata.py` with 4 new contract tests:
  - `test_ci_timeout_and_stale_workflow_guardrails`: verifies CI matrix runner timeout protection and stale issue/PR lifecycle configuration.
  - `test_gitignore_multihost_and_lock_hardening`: validates multi-host sync conflict protection (`*-WORKSTATION*`, `*conflicted copy*`), canonical lock patterns, and cache directory exclusions.
  - `test_pyproject_optional_dependencies`: checks PEP 621 optional dependency specifications for test and dev environments.
  - `test_changelog_release_0_2_2`: verifies release notes integrity for 0.2.2 technical hygiene and maintenance pass.

### Changed
- Hardened CI matrix workflow in `.github/workflows/ci.yml` with `timeout-minutes: 15` job guardrails to prevent runaway runner processes across all matrix operating systems (Ubuntu, Windows, macOS).
- Hardened `.gitignore` with comprehensive multi-host sync conflict rules (`*-WORKSTATION*`, `*-ASUS-GEI*`, `* (kopie)*`, `* (copy)*`, `*conflicted copy*`), lock patterns (`uv.lock`, with explicit `!package-lock.json` exemption), and cache directories (`.mypy_cache/`, `.tox/`, `.turbo/`, `*.orig`, `*.rej`).
- Enriched `[tool.ruff.lint]` configuration in `pyproject.toml` with `RUF022` for standard export list formatting.
- Synchronized version to `0.2.2` across `VERSION`, `pyproject.toml`, `ellmos-module.v2.json`, `README.md`, `README_de.md`, and `llms.txt`.
- Synchronized Shields.io badges in `README.md` and `README_de.md` for version 0.2.2, verification timestamp `2026--09--12`, and updated passing test suite status.
- Updated `llms.txt` verification timestamp to `2026-09-12` with 100% green contract test status.

## [0.2.1] - 2026-09-11

### Added
- Upgraded bilingual documentation landing pages (`README.md` and `README_de.md`) to 15-point quick navigation with mutual anchor parity:
  - Added dedicated section `#third-party-licenses--transparency` (`#drittanbieter-lizenzen--transparenz`) documenting open-source components, 100% local-first zero-egress posture, and unprivileged user-mode execution.
  - Added dedicated section `#marketing--target-personas` (`#marketing--zielgruppen`) with 4 distinct personas, high-intent discovery search queries, and 4-way competitive matrix.
- Comprehensive 4-way competitive matrix comparing `ai-media-editor` against Cloud SaaS (Descript / ElevenLabs), Heavy NLEs (Premiere / DaVinci), and Raw CLI scripts (FFmpeg / Shell).
- Formalized 4 target personas in `MARKETING-LOG.txt`: Autonomous AI Coding Agent Developers, Local-First Podcasters & Content Creators, AI Video & Motion Graphics Engineers, and Enterprise Media Security & Compliance Officers.
- Dual-Mermaid visual architecture diagrams in both English and German:
  - 5-Tier System Architecture Flowchart (`flowchart TB`) spanning media intake, orchestrator preflight, processing engines, agentic interaction layer, and deterministic export.
  - End-to-End Execution Lifecycle Sequence Diagram (`sequenceDiagram` with `autonumber`) illustrating preflight inspection, local STT routing, Scribe JSON generation, contact-sheet rendering, pause cut detection, and zero-egress output assembly.
- Formalized 10 Governance & Runtime Invariants table (`INV-LOCAL-01` through `INV-SLA-10`) guaranteeing local-first execution, unprivileged operation, preview safety, deterministic synthesis, and traversal protection.
- Sibling Ecosystem & Partner Matrix cross-linking 16 partner repositories across `ellmos-ai`, `entertain-and-more`, `dev-bricks`, `file-bricks`, `doc-bricks`, and `open-bricks`.
- Third-party open-source licenses inventory in `THIRD_PARTY_LICENSES.md` detailing upstream packages, licenses, and repositories.
- Expanded automated contract test suite in `tests/test_metadata.py` validating 15-point navigation, mutual anchor parity, dual-mermaid diagrams, governance invariants, sibling matrix, third-party licenses audit, and marketing log.

### Changed
- Standardized `pyproject.toml` with `version = "0.2.1"`, `addopts = "-ra -v"` and URLs for `Third-Party Licenses`, `Marketing Log`, and `LLM Ready`.
- Bumped version to `0.2.1` across `VERSION`, `ellmos-module.v2.json`, `pyproject.toml`, `README.md`, `README_de.md`, and `CHANGELOG.md`.
- Updated `llms.txt` verification timestamp to `2026-09-11` with verified 100% green test suite status, governance invariants, and 15-point navigation.
- Hardened `.gitignore` against multi-host conflict copies (`*.sync-temp-*`, `*-ASUS-GEI.*`) and lock patterns (`LOCK`, `LOCK.permissions.json`).

## [0.2.0] - 2026-09-09

### Added
- Multi-OS GitHub Actions CI matrix workflow (`.github/workflows/ci.yml`) across Ubuntu, Windows, and macOS on Python 3.10, 3.11, 3.12, and 3.13 with concurrency group (`cancel-in-progress: true`), `actions/checkout@v4`, `actions/setup-python@v5`, pip caching, and bytecode compilation gate (`python -m compileall -q .`).
- Automated repository contract test suite in `tests/test_metadata.py` with 10 contract tests verifying version consistency (`0.2.0`), manifest integrity, documentation links without local file URI schemes, `llms.txt` freshness, CI workflow parity, bilingual `SECURITY.md` SLAs, `.gitignore` patterns, and CLI modes smoke.
- Parent organization (`https://github.com/ellmos-ai`) and umbrella ecosystem (`https://github.com/open-bricks`) URLs, OS classifiers, and standardized tool configurations in `pyproject.toml`.
- Bilingual security policy in `SECURITY.md` (English & Deutsch) with formal 48h initial response SLA, 5-business-day triage commitment, supported versions table (`0.2.x`), maintainer contacts (`security@open-bricks.org`, `security@ellmos.ai`, `support@lukasgeiger.com`, `lukas@open-bricks.org`), and GitHub private vulnerability reporting.
- Shields.io CI status, Security SLA, and Ecosystem badges in `README.md` and `README_de.md`.

### Changed
- Hardened `.gitignore` against multi-host synchronization conflicts (`*.sync-conflict-*`, `*-CONFLIT-*`, `*-conflict-*`), multi-agent locks (`LOCK.*`, `*.lock`, `LOCK*.txt`), wheel smoke artifacts (`wheelhouse/`, `.wheel-smoke/`), and temporary files (`*.tmp`, `*.bak`, `*.swp`, `*~`, `*.log`).
- Updated `llms.txt` verification timestamp to `2026-09-09` with test count parity and ecosystem references.
- Synchronized Shields.io test status badges in `README.md` and `README_de.md` to verified pytest count (56 passed).
- Added German README (`README_de.md`, full 1:1 translation) and a language switcher in both files; `llms.txt` lists the new file. Language stage: **Core (DE+EN)** reached. First execution of the idle-language-pass policy P-006 (`.SYNC/_policies/library/`).

### Fixed
- Use real German umlauts in user-facing use-case labels and next-step CLI output.

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
