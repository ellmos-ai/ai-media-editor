"""Protocol tests for the Open Ocean owned-process worker (parent side simulated)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from ai_media_editor.ocean_worker import PROTOCOL, job_id, valid_checkpoint

WORKER = Path(__file__).resolve().parents[1] / "ai_media_editor" / "ocean_worker.py"


def wait_for(path: Path, timeout: float = 10.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
        time.sleep(0.05)
    raise AssertionError(f"{path.name} not written")


class OceanWorkerProtocolTest(unittest.TestCase):
    def run_worker(self, run_dir: Path, job: list[str], resume: dict | None, env: dict | None = None):
        identity = {"schema": PROTOCOL, "grant": {"request_id": "r1", "epoch": 1}, "execution_identity": "e1"}
        (run_dir / "start.json").write_text(json.dumps({**identity, "resume": resume}), encoding="utf-8")
        worker_env = {**os.environ, **(env or {}), "OCEAN_RESOURCE_RUN_DIR": str(run_dir)}
        proc = subprocess.Popen([sys.executable, "-I", "-S", str(WORKER), "--", *job], env=worker_env)
        return proc, identity

    def test_checkpoint_after_job_and_no_rerun_on_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "marker.txt"
            job = [sys.executable, "-c", "import sys; open(sys.argv[1], 'a').write('x')", str(marker)]
            payloads = []
            for attempt in range(2):
                run_dir = Path(tmp) / f"run{attempt}"
                run_dir.mkdir()
                proc, identity = self.run_worker(run_dir, job, payloads[-1] if payloads else None)
                try:
                    self.assertEqual(wait_for(run_dir / "ready.json"), identity)
                    (run_dir / "checkpoint.request.json").write_text(json.dumps(identity), encoding="utf-8")
                    answer = wait_for(run_dir / "checkpoint.json")
                    self.assertIs(answer["quiescent"], True)
                    self.assertEqual({k: answer[k] for k in identity}, identity)
                    self.assertTrue(valid_checkpoint(answer["payload"], job_id(job)))
                    self.assertEqual(answer["payload"]["exit_code"], 0)
                    self.assertIsNone(proc.poll(), "worker must stay alive until the owner stops it")
                    payloads.append(answer["payload"])
                finally:
                    proc.kill()
                    proc.wait()
            self.assertEqual(marker.read_text(encoding="utf-8"), "x", "resume must not rerun the job")

    def test_remote_compute_is_refused_before_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            (home / "config").mkdir(parents=True)
            (home / "config" / "settings.json").write_text('{"compute": {"prefer": "mac"}}', encoding="utf-8")
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            proc, _ = self.run_worker(run_dir, [sys.executable, "-c", "pass"], None,
                                      {"AI_MEDIA_EDITOR_HOME": str(home)})
            self.assertEqual(proc.wait(timeout=10), 2)
            self.assertFalse((run_dir / "ready.json").exists())

    def test_fits_frozen_python_bound(self):
        self.assertLessEqual(WORKER.stat().st_size, 8192)


if __name__ == "__main__":
    unittest.main()
