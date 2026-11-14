# Release-gate fixture

`fixture.mp4` is the end-to-end input for `tests/e2e/release_gates.py` and `tests/e2e/ocean_gate.py`
(task 1242). It is fully synthetic and contains no third-party recording, footage, music or voice.

| Property | Value |
|---|---|
| Container / streams | MP4, H.264 320x180 @ 25 fps, AAC mono 22.05 kHz |
| Duration / size | 7.62 s / 191,511 bytes |
| SHA-256 | `ce60c392e98b3fa458b8e433cf78c49ce36919017c73cd9ba5adc37c4db07fc5` |
| Video | ffmpeg `lavfi` `testsrc2` test pattern |
| Audio | eSpeak NG 1.52.0 formant synthesis (via `espeakng-loader` 0.2.4, voice `en-us`, 145 wpm), two takes joined by 1.5 s of `anullsrc` silence |
| Generated | 2026-11-14 on macOS 27.2 arm64, ffmpeg 8.1.1, by `make_fixture.sh` |

Spoken text (expected transcript):

1. "This is a synthetic test clip for the media editor."
2. *(1.5 s pause: the gate expects a strong cut marker `✂✂` in `cut_view.md`)*
3. "The second take starts after a clear pause."

eSpeak NG (GPL-3.0) is used only as a generator and is not distributed with this repository. The
fixture itself is covered by the repository's MIT license.

Regenerate with `PYTHON=<python with espeakng-loader==0.2.4> sh tests/e2e/fixture/make_fixture.sh`
(needs ffmpeg/ffprobe). Other ffmpeg/x264 builds may produce different bytes; the gates check
content (streams, duration, transcript keywords, pause), not the hash.
