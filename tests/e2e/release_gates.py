"""Real integration gates for the stable release (task 1243).

Runs the real tools against the synthetic fixture in ``tests/e2e/fixture`` and prints one
JSON line per gate plus a final ``GATE_OK`` / ``GATE_FAIL`` marker (SSH callers cannot rely
on remote exit codes, so the marker is the success signal).

  ffmpeg  ffprobe the fixture + ``editor.py frames --contact-sheet``
  stt     ``editor.py prepare`` locally (faster-whisper) -> transcript, takes_packed, cut_view
  render  video-use ``helpers/render.py`` on an EDL built from the stt transcript
  ssh     ``editor.py prepare`` with compute.prefer=mac against a real SSH host, then a
          readback that the isolated remote job directory was removed

Example (Mac Studio, all local gates):
  python tests/e2e/release_gates.py --python venv/bin/python --video-use video-use \
      --gates ffmpeg,stt,render
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "e2e" / "fixture" / "fixture.mp4"
KEYWORDS = ("synthetic", "second", "pause")


def run(cmd: list[str], env: dict | None = None, timeout: int = 1800) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env, timeout=timeout)


def probe(path: Path) -> dict:
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
               "-of", "json", str(path)])
    data = json.loads(out.stdout or "{}")
    return {"duration": float(data.get("format", {}).get("duration", 0)),
            "streams": sorted(s["codec_type"] for s in data.get("streams", []))}


def make_home(args, prefer: str) -> tuple[Path, dict]:
    home = Path(tempfile.mkdtemp(prefix="ame-gate-"))
    (home / "config").mkdir()
    settings = {
        "compute": {"prefer": prefer, "fallback": "local"},
        "mac": {"host": args.remote_host or "unused", "user": args.remote_user or "unused",
                "ssh_key": args.ssh_key or "unused", "venv_activate": args.remote_venv_activate or "true",
                "workdir": args.remote_workdir or "unused", "connect_timeout": 12},
        "engines": {"single_speaker": "faster", "multi_speaker": "faster"},
        "models": {"faster_local": args.model, "faster_mac": args.model},
        "language": "en",
        "paths": {"tools_root": str(Path(args.video_use).parent), "venv_python": args.python,
                  "video_use": args.video_use},
    }
    (home / "config" / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    return home, {**os.environ, "AI_MEDIA_EDITOR_HOME": str(home), "PYTHONIOENCODING": "utf-8"}


def prepare(args, prefer: str) -> tuple[dict, Path, str]:
    home, env = make_home(args, prefer)
    r = run([args.python, str(REPO / "editor.py"), "prepare", str(FIXTURE), "--mode", "3",
             "--project", "fixture"], env=env)
    edit = home / "projects" / "fixture" / "edit"
    transcript = edit / "transcripts" / "fixture.json"
    words = json.loads(transcript.read_text(encoding="utf-8"))["words"] if transcript.is_file() else []
    text = " ".join(w.get("text", "") for w in words if w.get("type") == "word").lower()
    cut_view = edit / "cut_view.md"
    checks = {
        "exit_0": r.returncode == 0,
        "keywords": all(k in text for k in KEYWORDS),
        "takes_packed": (edit / "takes_packed.md").is_file() and (edit / "takes_packed.md").stat().st_size > 0,
        "strong_pause": cut_view.is_file() and "✂✂" in cut_view.read_text(encoding="utf-8"),
    }
    return {"checks": checks, "transcript": text[:160], "tail": (r.stdout + r.stderr)[-400:]}, edit, r.stdout


def gate_ffmpeg(args) -> dict:
    version = run(["ffmpeg", "-version"]).stdout.splitlines()[0]
    info = probe(FIXTURE)
    home, env = make_home(args, "local")
    r = run([args.python, str(REPO / "editor.py"), "frames", str(FIXTURE), "--project", "fixture",
             "--contact-sheet", "--width", "160"], env=env)
    edit = home / "projects" / "fixture" / "edit"
    checks = {"streams_av": info["streams"] == ["audio", "video"], "duration_4_15s": 4 < info["duration"] < 15,
              "frames_exit_0": r.returncode == 0, "frame_view_md": (edit / "frame_view.md").is_file()}
    return {"checks": checks, "version": version, "probe": info}


def gate_render(args, edit: Path) -> dict:
    transcript = edit / "transcripts" / "fixture.json"
    if not transcript.is_file():
        return {"checks": {"stt_transcript_present": False}}
    words = [w for w in json.loads(transcript.read_text(encoding="utf-8"))["words"] if w.get("type") == "word"]
    gaps = [(words[i + 1]["start"] - words[i]["end"], i) for i in range(len(words) - 1)]
    _, cut = max(gaps)  # the deliberate pause between the two takes
    pad = 0.08
    ranges = [{"source": "fx", "start": max(0.0, words[0]["start"] - pad), "end": words[cut]["end"] + pad},
              {"source": "fx", "start": words[cut + 1]["start"] - pad, "end": words[-1]["end"] + pad}]
    edl = edit / "edl.json"
    edl.write_text(json.dumps({"sources": {"fx": str(FIXTURE)}, "ranges": ranges}), encoding="utf-8")
    out = edit / "final.mp4"
    r = run([args.python, str(Path(args.video_use) / "helpers" / "render.py"), str(edl), "-o", str(out),
             "--no-subtitles"])
    expected = sum(x["end"] - x["start"] for x in ranges)
    info = probe(out) if out.is_file() else {"duration": 0, "streams": []}
    checks = {"exit_0": r.returncode == 0, "streams_av": info["streams"] == ["audio", "video"],
              "duration_matches_edl": abs(info["duration"] - expected) < 0.5}
    return {"checks": checks, "expected_s": round(expected, 2), "probe": info,
            "tail": (r.stdout + r.stderr)[-300:]}


def gate_ssh(args) -> dict:
    # prepare() silently falls back to local STT; a caller python without faster-whisper turns
    # that fallback into a fast failure instead of a heavy run on the calling machine.
    if run([args.python, "-c", "import faster_whisper"]).returncode == 0:
        return {"checks": {"caller_python_without_stt_stack": False}}
    result, _, stdout = prepare(args, "mac")
    result["checks"]["remote_used"] = "[mac] fertig" in stdout
    ssh = ["ssh", "-i", args.ssh_key, "-o", "BatchMode=yes", f"{args.remote_user}@{args.remote_host}"]
    left = run(ssh + [f"ls -d {args.remote_workdir}/ai_media_* 2>/dev/null | wc -l; echo READBACK_OK"])
    count = re.search(r"(\d+)\s+READBACK_OK", left.stdout)
    result["checks"]["remote_cleanup"] = bool(count) and count.group(1) == "0"
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--python", default=sys.executable, help="venv python with the locked runtime")
    ap.add_argument("--video-use", required=True, help="browser-use/video-use checkout")
    ap.add_argument("--model", default="small")
    ap.add_argument("--gates", default="ffmpeg,stt,render")
    ap.add_argument("--remote-host")
    ap.add_argument("--remote-user")
    ap.add_argument("--ssh-key")
    ap.add_argument("--remote-venv-activate")
    ap.add_argument("--remote-workdir")
    args = ap.parse_args()
    gates = args.gates.split(",")
    ok, edit = True, None
    for name in gates:
        started = time.monotonic()
        if name == "ffmpeg":
            result = gate_ffmpeg(args)
        elif name == "stt":
            result, edit, _ = prepare(args, "local")
        elif name == "render":
            result = gate_render(args, edit) if edit else {"checks": {"stt_gate_ran_first": False}}
        elif name == "ssh":
            result = gate_ssh(args)
        else:
            raise SystemExit(f"unknown gate {name}")
        passed = all(result["checks"].values())
        ok &= passed
        print(json.dumps({"gate": name, "pass": passed, "seconds": round(time.monotonic() - started, 1),
                          **result}, ensure_ascii=False), flush=True)
    print("GATE_OK" if ok else "GATE_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
