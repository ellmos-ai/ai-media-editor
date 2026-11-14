# Pre-Release TODO: ai-media-editor

**Last review:** 2026-11-14

**Target repository:** `ellmos-ai/ai-media-editor`

**Status:** Release-Gates 1240–1245 grün (Belege in [`RELEASE_GATE.md`](RELEASE_GATE.md)); Stable-Tag vorbereitet, Freigabe offen

## Completed safety and correctness gates

The eleven completed entries previously listed here were transferred verbatim to
[`DONE.md`](DONE.md) on 2026-09-05. Open release work remains below.

## Remaining before a stable release

The following Taskplan items decompose the former release bullets into independently
verifiable steps. Detailed source, acceptance criteria, verification path,
dependencies, `effort`, `scope`, and priority rationale are stored with the
corresponding Taskplan task.

- [x] **Task 1240** — Unterstützte STT-/video-use-Umgebungsmatrix entscheiden und dokumentieren
  (`effort=special`, `scope=local`, `priority=high`). Erledigt 2026-11-14: Windows 11 x64 und macOS
  arm64 mit Python 3.12 für STT und Render, Linux nur CI-Unit-Tests (`RELEASE_GATE.md`).
- [x] **Task 1241** — Reproduzierbare Dependency-Locks für die unterstützten Plattformen implementieren
  (`effort=medium`, `scope=local`, `priority=high`; abhängig von 1240). Erledigt 2026-11-14:
  `requirements/runtime-*-py312.txt` mit Hashes, je Plattform erzeugt; `av<19` wegen faster-whisper 1.2.1.
- [x] **Task 1242** — Rechtegeklärtes reproduzierbares End-to-End-Fixture für die Kernpipeline hinzufügen
  (`effort=special`, `scope=local`, `priority=high`; abhängig von 1240). Erledigt 2026-11-14:
  `tests/e2e/fixture/` (testsrc2 + eSpeak NG, bitgleich reproduziert).
- [x] **Task 1243** — Reale ffmpeg-, STT-, SSH- und video-use-Integrationsgates ausführen und dokumentieren
  (`effort=special`, `scope=local`, `priority=high`; abhängig von 1240–1242). Erledigt 2026-11-14 auf
  dem Mac Studio und per SSH vom Laptop; dabei zwei Fehler behoben (SSH-Transfer, Contact-Sheet).
- [x] **Task 1244** — Öffentliche Python-API- und Docstrings auf Englisch normalisieren
  (`effort=medium`, `scope=local`, `priority=medium`).
- [x] **Task 1245** — Versionsführung vor dem Stable-Release klären
  (`effort=special`, `scope=local`, `priority=high`). Erledigt 2026-11-14: alle Quellen und das
  zuletzt gebaute Wheel stehen auf 0.2.3; 0.2.3 bleibt die eine Version (Version-Freeze), nur
  `RELEASE_GATE.md` (0.2.0) war veraltet.
- [ ] **Task 1246** — Stable-Release-Tags und Badges erst nach vollständigem Gate-Nachweis vorbereiten
  (`effort=special`, `scope=local`, `priority=high`; abhängig von 1240–1245 und expliziter Freigabe).
  Vorbereitet 2026-11-14 (Befehle in `RELEASE_GATE.md`); offen: Freigabe durch Lukas und Wahl der
  Release-Version (Vorschlag 0.3.0, Alternative 1.0.0).

## Offene Befunde aus den Release-Gates (2026-11-14)

- [ ] `prepare` ignoriert `compute.fallback` aus `settings.json`: Jeder Remote-Fehler fällt still auf
  lokale STT zurück und rechnet dann auf dem aufrufenden Rechner. Nächster Schritt: `fallback="none"`
  respektieren (Abbruch statt lokaler Rechnung) plus Unit-Test.
- [ ] `doctor` prüft auf dem Remote-Host `faster_whisper` **und** `whisperx`, obwohl der Standard ohne
  WhisperX auskommt → falsches XX bei Standard-Setups. Nächster Schritt: `whisperx` nur prüfen, wenn
  `engines.multi_speaker == "whisperx"`.
- [ ] Open-Ocean-Produktivzulassung für Pipeline 3b: geprüftes Workload-Profil
  (`ocean-reviewed-workload-profile.v1`) für den 3b-Job auf dem Mac messen und vom Operator freigeben
  lassen (Details in `RELEASE_GATE.md`).

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

Release gates: `tests/e2e/release_gates.py` and `tests/e2e/ocean_gate.py` (see `RELEASE_GATE.md`).

Current result (2026-11-14, Mac Studio, locked runtime, commit `46fe477`): **112 tests passed**, Ruff
clean; ffmpeg/STT/render/SSH/Ocean gates `GATE_OK`. Earlier local result (2026-07-15): 38 tests.
Optional cloud providers and WhisperX are still not claimed.

## STATUS

| Category | Status | Notes |
|---|---|---|
| Secrets / private media | Green | Excluded and covered by tests/docs |
| Unit and static checks | Green | 112 tests (2026-11-14, Mac), Ruff, AST, CLI smoke |
| Remote command handling | Green | Quoting, isolation, validation, cleanup regression-tested; real SSH gate green |
| Dependency reproducibility | Green | Hash locks for Windows x64 and macOS arm64 (Python 3.12) |
| Real integration | Green | ffmpeg, faster-whisper, video-use render, SSH, Ocean 3b (2026-11-14) |
| Overall | Release-ready | Stable tag prepared; maintainer approval pending (task 1246) |

## Intentionally excluded

- Real `config/settings.json`, `projects/` content, media, tokens, venvs, and tool caches.
- Machine-specific OpenMontage reference documents.
- Heavy third-party tools and models; they live under a user-selected `<TOOLS_ROOT>` outside synced folders.
