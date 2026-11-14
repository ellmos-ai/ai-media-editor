# Release Gate — ai-media-editor

**Reviewed:** 2026-11-14
**Version:** 0.2.3 (single version across all sources, see task 1245)
**Decision:** tasks 1240–1245 green on the supported matrix; the stable tag is prepared but not
created — it needs maintainer approval (task 1246).

## Supported environment matrix (task 1240)

| Platform | Role | Python | STT (faster-whisper) | Render (ffmpeg, video-use) | SSH remote STT | Lock |
|---|---|---|---|---|---|---|
| Windows 11 x64 | editing workstation | 3.12 | supported | supported | caller side (OpenSSH client) | `requirements/runtime-windows-x64-py312.txt` |
| macOS arm64 (Apple Silicon) | compute host, heavy runs | 3.12 | supported | supported | remote side | `requirements/runtime-macos-arm64-py312.txt` |
| Linux x64 | CI only | 3.10–3.13 | not supported | not supported | — | none (unit tests, Ruff, CLI smoke) |

- Rationale: these are the hosts actually in use; heavy runs belong on the macOS compute host.
- Measured deviations: the laptop's private `config/settings.json` uses `compute.prefer=local` with an
  empty remote block, so real Windows use so far was local STT — covered by the Windows row.
  `pyproject.toml` classifiers and the module manifest still list Linux and Python 3.10–3.13; they
  describe where the unit tests pass, not a supported media runtime.
- Outside the matrix (best effort, not locked): WhisperX/pyannote (HF token, torch), CUDA/GPU,
  HyperFrames (Node ≥ 22, npm toolchain), OpenMontage.
- Windows requirement: run the editor and the video-use helpers with `PYTHONIOENCODING=utf-8`
  (as in `CLAUDE.md`); video-use `render.py` prints `→` and aborts on a cp1252 console otherwise
  (seen on the clean `windows-latest` runner, 2026-11-14).
- External pins: `browser-use/video-use` at `cf12ac3`; ffmpeg ≥ 8 from the host. Homebrew ffmpeg 8.1.1
  has no `drawtext`; contact sheets then fall back to unlabeled tiles (fixed in this release, see below).

## Dependency locks (task 1241)

`requirements/runtime.in` lists the top-level runtime. Each lock is compiled **on its platform** with
`uv pip compile requirements/runtime.in --generate-hashes --python-version 3.12 --python-platform <triple>`
(uv 0.12.5 on Windows, 0.13.8 on macOS) and installed with
`python -m pip install --require-hashes -r requirements/runtime-<platform>-py312.txt`.

| Lock | Pins | Hashes | Platform-specific difference |
|---|---|---|---|
| `runtime-windows-x64-py312.txt` | 55 | 1322 | onnxruntime 1.32.0, colorama |
| `runtime-macos-arm64-py312.txt` | 58 | 1326 | onnxruntime 1.23.2, coloredlogs, humanfriendly, sympy, mpmath |

`av` is capped below 19: av 19.0.2 removed `av.open(metadata_errors=...)`, which faster-whisper 1.2.1
(the latest release) still passes — every transcription failed with `TypeError` (measured 2026-11-14;
av 18.1.0 and 17.1.0 accept it). The macOS lock was installed into a fresh venv with `--require-hashes`
(pip exit 0, 60 s) and all macOS gates below ran in that venv. The workflow
`.github/workflows/release-gates.yml` installs each lock on a clean GitHub runner and runs the fixture gates.

## Fixture (task 1242)

`tests/e2e/fixture/fixture.mp4`: 7.62 s, fully synthetic (ffmpeg `testsrc2` + eSpeak NG speech with a
1.5 s pause), no third-party media. Provenance, hash and regeneration: `tests/e2e/fixture/README.md`.
Regenerating on the Mac Studio reproduced the committed file bit for bit (same SHA-256).

## Integration gates (task 1243)

Runner: `tests/e2e/release_gates.py` (ffmpeg, stt, render, ssh) and `tests/e2e/ocean_gate.py`.
SSH does not return the remote exit code, so a gate counts as passed only with the `GATE_OK` marker
in its output plus the per-check JSON line.

| Gate | Host | Command | Versions | Duration | Evidence |
|---|---|---|---|---|---|
| ffmpeg | Mac Studio, macOS 27.2 arm64 | `release_gates.py --gates ffmpeg,stt,render --model large-v3` | ffmpeg 8.1.1 | 0.2 s | ffprobe audio+video 7.62 s; `editor.py frames --contact-sheet` wrote `frame_view.md`; `GATE_OK` |
| stt | Mac Studio | same run | faster-whisper 1.2.1, ctranslate2 4.9.0, av 18.1.0, `large-v3` CPU int8 | 8.1 s | verbatim transcript, `takes_packed.md`, `✂✂` pause in `cut_view.md`; `GATE_OK` |
| video-use render | Mac Studio | same run | video-use `cf12ac3` `helpers/render.py` | 1.6 s | 6.17 s output for a 6.05 s two-range EDL, audio+video; `GATE_OK` |
| ssh remote STT | Windows 11 laptop (Python 3.12.10 without STT stack) → Mac Studio over Tailscale | `release_gates.py --gates ssh --model large-v3 ...` | OpenSSH client from Git for Windows | 13.5 s | `[mac] fertig`, verbatim transcript, remote job directory removed (readback count 0); `GATE_OK` |
| unit suite + Ruff | Mac Studio, locked runtime | `python -X utf8 -m pytest -q`, `ruff check .` | pytest, Ruff 0.15.18 | 22 s | 112 passed, Ruff clean |
| Ocean 3b binding | Mac Studio | `PYTHONPATH=<open-ocean> python tests/e2e/ocean_gate.py ...` | open-ocean `72759fc` | 8.1 s | verified checkpoint `exit_code 0`, owned tree exited, slot released; `GATE_OK` |
| Windows clean runner | GitHub `windows-latest`, Python 3.12.10 | workflow `Release gates`, run 43615603984 (`210cd4d`) | Windows lock (`--require-hashes`), ffmpeg 9.0.2 gyan.dev, `small` CPU int8 | ffmpeg 0.4 s, stt 11.4 s, render 5.4 s | verbatim transcript, `✂✂` pause, 6.31 s render for a 6.25 s EDL; `GATE_OK` |
| macOS clean runner | GitHub `macos-latest` (arm64) | same run | macOS lock (`--require-hashes`), ffmpeg 9.0.2, `small` CPU int8 | ffmpeg 0.3 s, stt 8.5 s, render 3.5 s | verbatim transcript, `✂✂` pause, 6.31 s render; `GATE_OK` |

Mac runs were repeated on a fresh clone of the final commit `210cd4d` (same results, suite 112
passed); the SSH gate was repeated from the laptop at `210cd4d` (15.5 s, `GATE_OK`). The unit suite is run on the Mac or in CI, not on the laptop.

### Defects found by these gates and fixed in this release

1. **SSH remote path was broken** with OpenSSH ≥ 9: `scp` defaults to SFTP and no longer shell-parses
   the quoted `"$HOME"/'...'` remote path, so every upload failed and `prepare` silently transcribed
   locally. Transfers now use `ssh … cat` through the remote shell.
2. **Contact sheets were empty** with ffmpeg builds lacking `drawtext` (Homebrew 8.1.1); they now fall
   back to unlabeled tiles and `frame_view.md` states the tile-to-second mapping.
3. **faster-whisper 1.2.1 + av 19** fail on every file; the locks cap `av<19`.

### Known limitations (open, see `TODO.md`)

- `prepare` ignores `compute.fallback`: any remote failure falls back to local STT. The SSH gate
  therefore refuses a caller interpreter that has faster-whisper installed.
- `doctor` requires `whisperx` on the remote host although the default engine does not use it.

## Version (task 1245)

Measured 2026-11-14: `VERSION`, `pyproject.toml`, `ellmos-module.v2.json` and the README version badge
say 0.2.3; the latest `CHANGELOG.md` release is 0.2.3 (2026-09-20); the last built wheel is
`ai_media_editor-0.2.3-py3-none-any.whl`. There is no git tag, no GitHub release and no PyPI upload.
Only this file (0.2.0) and the task text in `TODO.md` were stale. Decision: 0.2.3 stays the single
version; no bump under the version freeze (T-20260920-167562623).

## Stable release (task 1246) — prepared, not executed

Not done here on purpose: no tag, no badge change, no GitHub release. Proposal (maintainer
confirmation open): release the gate-verified state as **0.3.0** — `[Unreleased]` adds features since
0.2.3 (tools port, Ocean worker, locks), and 0.3.0 keeps the pre-1.0 API signal; choose 1.0.0 instead if
the release should promise API stability. Tagging `v0.2.3` on today's HEAD is not proposed: 0.2.3 is
documented as the 2026-09-20 state and does not contain the gate fixes.

After approval, on the merged `main`:

```bash
NEW=0.3.0
# 1. bump VERSION, pyproject.toml, ellmos-module.v2.json, README version badges (all languages)
# 2. CHANGELOG: rename [Unreleased] to [$NEW] - <date>, open a new empty [Unreleased]
#    (tests/test_metadata.py pins the version and the [Unreleased] heading; update them in the same commit)
# 3. badges: tests count from the latest green CI run, "last checked" date
git tag -a "v$NEW" -m "ai-media-editor $NEW: release gates 1240-1245 green"
git push origin "v$NEW"
gh release create "v$NEW" --notes-file <release-notes.md>
```

## Open Ocean binding (pipeline 3b `video-render`)

- Contract: open-ocean PR #69 (pipeline catalogue, `reference-only`, executor is an abstract token
  without a module field) and PR #70 (`OwnedProcessExecutor`, worker protocol
  `ocean-owned-process.v1`).
- Implementation: `ai_media_editor/ocean_worker.py`, stdlib-only and below 8 KiB so it also runs in the
  `frozen-python` source mode that reviewed production profiles require. The manifest declares it as
  `adapters[]` seam `ocean-owned-process.v1` → `open-ocean`.
- Evidence: `tests/e2e/ocean_gate.py` (fixture admission) and `tests/test_ocean_worker.py`.
- Boundaries: a checkpoint is answered once the running job has exited (no mid-job preemption);
  remote SSH STT is refused inside an owned process (remote workers need their own adapter).
- Next step (operator): production admission needs a reviewed workload profile
  (`ocean-reviewed-workload-profile.v1` + measurement evidence, `approved_by` the operator). Measure the
  3b job on the Mac with `OwnedProcessExecutor.measure_usage`, then approve. No open-ocean change is
  required for that.

## Rerun

```bash
# macOS compute host, in a venv created from the macOS lock
python tests/e2e/release_gates.py --python "$VENV/bin/python" --video-use <video-use@cf12ac3> --gates ffmpeg,stt,render
# Windows caller -> SSH host; caller python WITHOUT faster-whisper
python tests/e2e/release_gates.py --python <plain python> --video-use <video-use> --gates ssh \
  --remote-host <host> --remote-user <user> --ssh-key <key> \
  --remote-venv-activate "source <venv>/bin/activate" --remote-workdir "~/<jobs dir>"
```

## Intentionally excluded

- Real `config/settings.json`, `projects/` content, private media, tokens, venvs, model caches.
- Host addresses and user names of the SSH gate (withheld here; the gate takes them as arguments).

## History: review of 2026-07-15 (candidate 0.2.0)

Verified green at that time:

- Independent review: no P0 findings; identified P1 correctness/security findings
  were addressed with regression coverage.
- `python -m unittest discover -s tests -v`: 38/38 passed.
- `ruff check .`: passed.
- All Python files parse; `python editor.py modes` and CLI help smokes pass.
- Transcript cache provenance, remote quoting/isolation/cleanup, token-file transfer,
  helper error propagation, frame freshness, label coverage, and path containment
  have focused tests.
- Manifest JSON and catalog schema contract are valid in the module workspace.
- Public docs disclose remote/full-media transfer and optional cloud-provider gates.

Guarded then and resolved by this review: no redistributable fixture, no real
ffmpeg/faster-whisper/SSH/video-use runs, no dependency matrix.
