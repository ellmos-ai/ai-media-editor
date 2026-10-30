from __future__ import annotations

import io
import json
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from ai_media_editor.tools import make_loop, qa_clips

try:
    import numpy as np
    import scipy  # noqa: F401

    from ai_media_editor.tools import atmo, synth

    HAVE_SCIPY = True
except ImportError:  # pragma: no cover - optional in minimal CI
    np = None  # type: ignore[assignment]
    synth = None  # type: ignore[assignment]
    atmo = None  # type: ignore[assignment]
    HAVE_SCIPY = False


ROOT = Path(__file__).resolve().parents[1]


class MakeLoopTests(unittest.TestCase):
    SAMPLE_CFG = {
        "pause_s": 8,
        "order": ["01-weisse-frau", "05-kuerbis-lacht"],
        "durations_s": {"01-weisse-frau": 26, "05-kuerbis-lacht": 30},
    }

    def test_build_ffmpeg_command_without_audio(self) -> None:
        cmd, pause_s, total = make_loop.build_ffmpeg_command(
            self.SAMPLE_CFG, Path("/tmp/renders"), Path("/tmp/out.mp4")
        )
        self.assertEqual(pause_s, 8.0)
        self.assertEqual(total, 26 + 30 + 2 * 8.0)
        self.assertIn("-filter_complex", cmd)
        flt = cmd[cmd.index("-filter_complex") + 1]
        self.assertIn("concat=n=4:v=1:a=0[v]", flt)
        self.assertIn("color=c=black:s=1920x1080:r=30:d=8.0", flt)
        self.assertNotIn("aac", cmd)

    def test_build_ffmpeg_command_with_pause_override_and_audio(self) -> None:
        cmd, pause_s, total = make_loop.build_ffmpeg_command(
            self.SAMPLE_CFG,
            Path("/tmp/renders"),
            Path("/tmp/out.mp4"),
            pause=12.0,
            audio=Path("/tmp/atmo.wav"),
        )
        self.assertEqual(pause_s, 12.0)
        self.assertEqual(total, 26 + 30 + 2 * 12.0)
        self.assertIn("2:a", cmd)
        self.assertIn("aac", cmd)
        self.assertIn("-shortest", cmd)

    def test_empty_order_raises_value_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "order"):
            make_loop.build_ffmpeg_command(
                {"pause_s": 8, "order": [], "durations_s": {}},
                "/tmp/renders",
                "/tmp/out.mp4",
            )

    def test_main_invokes_ffmpeg_and_prints_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "loop.json"
            cfg_path.write_text(json.dumps(self.SAMPLE_CFG), encoding="utf-8")
            out_path = Path(tmp) / "loop.mp4"
            buf = io.StringIO()
            with (
                mock.patch.object(make_loop.subprocess, "run") as run_mock,
                redirect_stdout(buf),
            ):
                make_loop.main([str(cfg_path), str(tmp), "-o", str(out_path), "--pause", "5"])
            run_mock.assert_called_once()
            self.assertIn("Loop: 2 Clips, Pause 5.0 s, Soll-Länge 66.0 s", buf.getvalue())


class QaClipsTests(unittest.TestCase):
    def test_build_xstack_layout(self) -> None:
        self.assertEqual(qa_clips.build_xstack_layout(1), "0_0")
        layout5 = qa_clips.build_xstack_layout(5)
        self.assertEqual(layout5.split("|"), ["0_0", "w0_0", "w0+w0_0", "w0+w0+w0_0", "0_h0"])

    def test_luma_computes_mean_and_max_with_and_without_numpy(self) -> None:
        fake_proc = subprocess.CompletedProcess([], 0, stdout=bytes([0, 10, 20, 30]), stderr=b"")
        with mock.patch.object(qa_clips.subprocess, "run", return_value=fake_proc):
            mean_val, max_val = qa_clips.luma("clip.mp4", 0.5)
            self.assertAlmostEqual(mean_val, 15.0)
            self.assertEqual(max_val, 30)

        with (
            mock.patch.object(qa_clips.subprocess, "run", return_value=fake_proc),
            mock.patch.object(qa_clips, "np", None),
        ):
            mean_fb, max_fb = qa_clips.luma("clip.mp4", 0.5)
            self.assertAlmostEqual(mean_fb, 15.0)
            self.assertEqual(max_fb, 30)

    def test_run_qa_writes_report_and_contact_sheet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            dst = Path(tmp) / "dst"
            src.mkdir()
            clip = src / "01-weisse-frau.mp4"
            clip.write_bytes(b"fake-mp4-data")

            probe_json = json.dumps({
                "streams": [{
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30/1",
                    "pix_fmt": "yuv420p",
                    "nb_frames": "780",
                }],
                "format": {"duration": "26.0"},
            })

            def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[object]:
                if cmd[0] == "ffprobe":
                    return subprocess.CompletedProcess(cmd, 0, stdout=probe_json, stderr="")
                if "-f" in cmd and "rawvideo" in cmd:
                    return subprocess.CompletedProcess(cmd, 0, stdout=bytes([0, 0, 2, 2]), stderr=b"")
                out_file = Path(cmd[-1])
                out_file.parent.mkdir(parents=True, exist_ok=True)
                out_file.write_bytes(b"jpg")
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            with (
                mock.patch.object(qa_clips.subprocess, "run", side_effect=fake_run),
                redirect_stdout(io.StringIO()),
            ):
                rep = qa_clips.run_qa(src, dst)

            self.assertIn("01-weisse-frau", rep)
            self.assertEqual(rep["01-weisse-frau"]["duration"], 26.0)
            self.assertEqual(rep["01-weisse-frau"]["first_frame_luma_mean_max"], (1.0, 2))
            self.assertTrue((dst / "qa.json").is_file())
            self.assertTrue((dst / "VORSCHAU_kontaktbogen.jpg").is_file())
            self.assertTrue((dst / "frames" / "01-weisse-frau_hoehepunkt.jpg").is_file())


@unittest.skipUnless(HAVE_SCIPY, "numpy/scipy nicht installiert")
class SynthAndAtmoTests(unittest.TestCase):
    def test_synth_instruments_and_filters_are_deterministic(self) -> None:
        assert np is not None and synth is not None
        s = synth
        a = s.chip_pulse(440.0, 0.15, 0.8, 0.5)
        b = s.chip_pulse(440.0, 0.15, 0.8, 0.5)
        self.assertTrue(np.array_equal(a, b))
        for sig in (
            s.chip_tri(330.0, 0.1, 0.7, 0.5),
            s.chip_hat(0.6, 0.8, open_=True),
            s.chip_snare(0.7, 0.8),
            s.chip_kick(0.8, 0.8),
            s.marimba(440.0, 0.1, 0.7, 0.6, legato=True),
            s.glock(880.0, 0.1, 0.6, 0.7, legato=True),
            s.pizz(220.0, 0.1, 0.8, 0.5),
            s.flute(523.25, 0.15, 0.6, 0.7, ocarina=True),
            s.shaker(0.5),
            s.woodblock(0.5),
            s.framedrum(0.6),
            s.fm_brass(330.0, 0.15, 0.7, 0.6),
            s.fm_bell(660.0, 0.15, 0.7, 0.6, legato=True),
            s.snare(0.6, brush=True),
            s.snare(0.6, brush=False),
            s.bdrum(0.8),
            s.cymbal(0.5),
        ):
            self.assertEqual(sig.ndim, 1)
            self.assertGreater(len(sig), 0)
            self.assertTrue(np.all(np.isfinite(sig)))
            self.assertGreater(float(np.max(np.abs(sig))), 0.0)

        ir = s.make_ir(0.2, 0.01, 4000, seed=3)
        self.assertEqual(ir.shape[1], 2)
        self.assertTrue(np.all(np.isfinite(ir)))

    def test_atmo_measure_parses_ebur128_and_guards_missing_summary(self) -> None:
        assert atmo is not None
        sample_stderr = (
            "[Parsed_ebur128_0 @ 0x0] Summary:\n"
            "  Integrated loudness:\n"
            "    I:         -16.1 LUFS\n"
            "    Threshold: -26.5 LUFS\n"
            "  True peak:\n"
            "    Peak:       -3.6 dBFS\n"
        )
        ok_proc = subprocess.CompletedProcess([], 0, stdout="", stderr=sample_stderr)
        with mock.patch.object(atmo.subprocess, "run", return_value=ok_proc):
            lufs, tp = atmo.measure("dummy.wav")
            self.assertAlmostEqual(lufs, -16.1)
            self.assertAlmostEqual(tp, -3.6)

        bad_proc = subprocess.CompletedProcess([], 1, stdout="", stderr="ffmpeg error without summary")
        with (
            mock.patch.object(atmo.subprocess, "run", return_value=bad_proc),
            self.assertRaisesRegex(RuntimeError, "ebur128 Summary nicht lesbar"),
        ):
            atmo.measure("dummy.wav")

    def test_atmo_master_converges_and_handles_all_iterations(self) -> None:
        assert np is not None and synth is not None and atmo is not None
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "out.wav"
            x = np.sin(2 * np.pi * 220 * np.arange(synth.SR // 4) / synth.SR)
            x_stereo = np.stack([x, x], axis=1)
            with mock.patch.object(
                atmo, "measure", side_effect=[(-18.0, -1.0), (-16.05, -3.7)]
            ):
                lufs, tp = atmo.master(x_stereo, wav_path, target=-16.0, tp_max=-3.5)
            self.assertAlmostEqual(lufs, -16.05)
            self.assertAlmostEqual(tp, -3.7)
            self.assertTrue(wav_path.is_file())

    def test_atmo_compose_renders_loopable_stereo_buffer(self) -> None:
        assert np is not None and synth is not None and atmo is not None
        cfg = {
            "pause_s": 2.0,
            "order": ["01-weisse-frau", "05-kuerbis-lacht"],
            "durations_s": {"01-weisse-frau": 3.0, "05-kuerbis-lacht": 3.0},
        }
        out, total_len = atmo.compose(cfg, pause=2.0)
        self.assertAlmostEqual(total_len, 10.0)
        self.assertEqual(out.shape, (int(10.0 * synth.SR), 2))
        self.assertTrue(np.all(np.isfinite(out)))
        self.assertGreater(float(np.max(np.abs(out))), 0.01)


@unittest.skipUnless(shutil.which("node") is not None, "node nicht auf PATH")
class HfxJsTests(unittest.TestCase):
    def test_fx_js_helpers_and_ft_immediate_render_false(self) -> None:
        fx_path = ROOT / "ai_media_editor" / "tools" / "fx.js"
        script = f"""
const assert = require('assert/strict');
global.document = {{
  createElementNS(ns, tag) {{
    return {{
      ns, tag, attrs: {{}}, children: [],
      setAttribute(k, v) {{ this.attrs[k] = String(v); }},
      appendChild(c) {{ this.children.push(c); return c; }}
    }};
  }}
}};
const HFX = require({json.dumps(str(fx_path))});

// 1. HFX.ft forces immediateRender: false on GSAP fromTo
const calls = [];
const fakeTl = {{
  fromTo(target, fromVars, toVars, pos) {{
    calls.push({{ target, fromVars, toVars, pos }});
    return 'tween-ref';
  }},
  to(target, vars, pos) {{
    calls.push({{ target, vars, pos }});
    if (vars.onUpdate) {{ target.t = vars.t; vars.onUpdate(); }}
    return 'drive-ref';
  }}
}};
const res = HFX.ft(fakeTl, '#ghost', {{ opacity: 0 }}, {{ opacity: 1, duration: 2 }}, 1.5);
assert.equal(res, 'tween-ref');
assert.equal(calls[0].toVars.immediateRender, false);
assert.equal(calls[0].toVars.opacity, 1);
assert.equal(calls[0].pos, 1.5);

// 2. Deterministic RNG & noise1
const r1 = HFX.rng(42), r2 = HFX.rng(42);
assert.equal(r1(), r2());
const n1 = HFX.noise1(7), n2 = HFX.noise1(7);
assert.equal(n1(1.25), n2(1.25));

// 3. Math & keyframe helpers
assert.equal(HFX.clamp(5, 0, 3), 3);
assert.equal(HFX.lerp(10, 20, 0.5), 15);
assert.equal(HFX.bump(0, 1, 3), 0);
assert.ok(Math.abs(HFX.bump(2, 1, 3) - 1) < 1e-9);
assert.equal(HFX.key(0, [[1, 10], [3, 20]]), 10);
assert.equal(HFX.key(4, [[1, 10], [3, 20]]), 20);

// 4. Piecewise path & SVG rigs (spider, bat)
const p = HFX.path([[0, 0, 0], [2, 10, 0]]);
assert.equal(p(1).x, 5);
assert.equal(p(1).moving, true);
const rootSvg = document.createElementNS(HFX.NS, 'svg');
const sp = HFX.spider(rootSvg, {{ size: 100, seed: 2, detail: true }});
sp.pose(0.5, 1.0, 1.2);
assert.equal(sp.g.tag, 'g');
const bt = HFX.bat(rootSvg, 80);
bt.flap(0.25);
assert.equal(bt.g.tag, 'g');
"""
        proc = subprocess.run(
            ["node", "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
