# Pre-Release TODO: ai-media-editor

**Last review:** 2026-07-15

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

- [ ] Define and test a reproducible external STT/video-use environment (supported Python version,
  faster-whisper/WhisperX/torch matrix, and locked dependency set per platform).
- [ ] Add a redistributable, rights-cleared end-to-end fixture covering media → transcript → pack → cut view.
- [ ] Run real ffmpeg, faster-whisper, optional WhisperX, SSH-host, and video-use integration checks on the
  supported Windows/macOS environments; unit tests deliberately mock these heavy/external paths.
- [ ] Finish English API/docstring normalization where public Python modules remain German-first.
- [ ] Add release tags/badges only after the environment and integration gates above are green.

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
