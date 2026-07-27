# Pre-Release TODO: ai-media-editor

**Last review:** 2026-07-27

**Target repository:** `ellmos-ai/ai-media-editor`

**Status:** hardened development build; not yet release-green

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

## Remaining before a stable release

The following Taskplan items decompose the former release bullets into independently
verifiable steps. Detailed source, acceptance criteria, verification path,
dependencies, `effort`, `scope`, and priority rationale are stored with the
corresponding Taskplan task.

- [ ] **Task 1240** — Unterstützte STT-/video-use-Umgebungsmatrix entscheiden und dokumentieren
  (`effort=special`, `scope=local`, `priority=high`).
- [ ] **Task 1241** — Reproduzierbare Dependency-Locks für die unterstützten Plattformen implementieren
  (`effort=medium`, `scope=local`, `priority=high`; abhängig von 1240).
- [ ] **Task 1242** — Rechtegeklärtes reproduzierbares End-to-End-Fixture für die Kernpipeline hinzufügen
  (`effort=special`, `scope=local`, `priority=high`; abhängig von 1240).
- [ ] **Task 1243** — Reale ffmpeg-, STT-, SSH- und video-use-Integrationsgates ausführen und dokumentieren
  (`effort=special`, `scope=local`, `priority=high`; abhängig von 1240–1242).
- [ ] **Task 1244** — Öffentliche Python-API- und Docstrings auf Englisch normalisieren
  (`effort=medium`, `scope=local`, `priority=medium`).
- [ ] **Task 1245** — Versionsführung 0.2.0 versus Changelog 0.2.2 vor dem Stable-Release klären
  (`effort=special`, `scope=local`, `priority=high`; Nutzer-/Maintainerentscheidung erforderlich).
- [ ] **Task 1246** — Stable-Release-Tags und Badges erst nach vollständigem Gate-Nachweis vorbereiten
  (`effort=special`, `scope=local`, `priority=high`; abhängig von 1240–1245 und expliziter Freigabe).

## TASKWRITER-Register

**2026-07-27 — Projekt:** `C:\_Local_DEV\repos\ai-media-editor`

- Gelesene Steuerdateien: `AGENTS.md`, `CLAUDE.md`, `README.md`, `TODO.md`,
  `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `RELEASE_GATE.md`,
  `docs/USECASES.md`, `production/OVERVIEW.md`, alle sechs `production/*/WORKFLOW.md`,
  `config/settings.example.json`, `pyproject.toml`, `requirements-dev.txt`,
  `.github/workflows/ci.yml`, `ellmos-module.v2.json`, `llms.txt` und `VERSION`.
- Ist-Stand: `main` ist sauber und ohne Projekt-Lock; der aufgezeichnete Fast-Gate-Stand
  bleibt 38 Tests, Ruff, AST/Import und CLI-Smoke grün. Reale STT-/ffmpeg-/SSH-/video-use-
  Läufe sind ausdrücklich nicht belegt.
- Neu formalisiert: sieben offene Aufgaben (1240–1246), davon fünf `special` und zwei
  `medium`, alle mit `scope=local`; keine Aufgabe wurde ausgeführt.
- Zusammengeführt: Die bisherigen fünf Stable-Release-Bullets wurden in die Tasks 1240–1244
  und 1246 zerlegt. Task 1245 dokumentiert zusätzlich die belegte Versionsabweichung
  zwischen `CHANGELOG.md` (0.2.2) und den Versionsquellen (0.2.0).
- Offene Entscheidungen: Supportumfang und Plattformmatrix, Rechteklärung bzw. Fixture,
  verfügbare externe Integrationsumgebungen, Versionssemantik und spätere Stable-Release-
  Freigabe. Kein Tag, Push, Upload oder Provider-Aufruf wurde autorisiert oder ausgeführt.

## Verification contract

```bash
python -m unittest discover -s tests -v
ruff check .
python editor.py modes
```

Current local result (2026-07-15): **38 tests passed**, Ruff clean, AST/import/CLI smoke green.
This does not claim that optional cloud providers, SSH infrastructure, STT models, or rendering tools
are available on a particular machine.

## STATUS

| Category | Status | Notes |
|---|---|---|
| Secrets / private media | Green | Excluded and covered by tests/docs |
| Unit and static checks | Green | 38 tests, Ruff, AST, CLI smoke |
| Remote command handling | Green | Quoting, isolation, validation, cleanup regression-tested |
| Dependency reproducibility | Open | Cross-platform STT/video-use lock matrix missing |
| Real integration | Open | ffmpeg/STT/SSH/video-use environment runs still required |
| Overall | Development | Hardened, but not a stable-release claim |

## Intentionally excluded

- Real `config/settings.json`, `projects/` content, media, tokens, venvs, and tool caches.
- Machine-specific OpenMontage reference documents.
- Heavy third-party tools and models; they live under a user-selected `<TOOLS_ROOT>` outside synced folders.
