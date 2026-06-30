# Pre-Release TODO: ai-media-editor

**Audit Date:** 2026-06-17
**Auditor:** Claude (for Lukas Geiger)
**Target Repo:** `ellmos-ai/ai-media-editor`

---

## BLOCKER

> Must be resolved before public release.

- [x] **Secrets:** No API keys/tokens/passwords in tracked files (HF token field empty; real `settings.json` gitignored).
- [x] **Private Data:** No personal host/user/IP in tracked files (Mac SSH/IP only in gitignored `settings.json`).
- [x] **Hardcoded Paths:** Personal paths neutralized to `<TOOLS_ROOT>` / `<OPENMONTAGE_DIR>` placeholders; resolved at runtime from `settings.json`.
- [x] **Database Files:** None tracked.
- [x] **.env Files:** None tracked (`.env` ignored).
- [x] **BACH Internals:** None.
- [x] **.gitignore:** Minimum entries present (`__pycache__`, `*.pyc`, `.env`, `*.db`, `.venv/`, `.idea/`, `.vscode/`, `data/`) + private config/projects/media.
- [x] **LICENSE:** MIT present.
- [x] **README.md:** English, complete (agent guide `CLAUDE.md` stays German by design).

## HIGH PRIORITY
- [ ] All docstrings in English (currently mixed DE/EN).
- [ ] Pin dependency versions for the external venv (video-use / faster-whisper / WhisperX).
- [ ] Add a short end-to-end example (sample recording → cut) to README.

## MEDIUM PRIORITY
- [ ] Add `CONTRIBUTING.md`, `SECURITY.md`.
- [x] Add `CHANGELOG.md`.
- [ ] GitHub Actions CI (lint + import smoke).

## LOW PRIORITY
- [ ] Test suite, badges.

## Intentionally Excluded
- No real `config/settings.json`, no `projects/` content, no media (gitignored).
- `docs/OPENMONTAGE-KOMPONENTEN.md` is a machine-specific local reference (gitignored).
- Heavy tools + venv live outside the repo (`<TOOLS_ROOT>`), not vendored.

---

## STATUS

| Category | Status | Notes |
|----------|--------|-------|
| Secrets | :green_circle: | HF token empty; real settings gitignored |
| Private Data (PII) | :green_circle: | Host/user/IP only in gitignored settings |
| .gitignore | :green_circle: | Minimum entries + private exclusions |
| Language (English) | :green_circle: | README English |
| BACH Internals | :green_circle: | None |
| Database Files | :green_circle: | None tracked |
| README.md | :green_circle: | Complete |
| LICENSE | :green_circle: | MIT |
| **Overall** | **READY** | Private; gate green |

**Audit Date:** 2026-06-17
**Gate Check Exit Code:** `0`

---

*Basis: MODULES/_templates/TODO_TEMPLATE.md*
