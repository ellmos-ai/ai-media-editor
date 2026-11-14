"""Ocean binding gate: pipeline 3b job through open-ocean's real OwnedProcessExecutor.

Starts ``ai_media_editor/ocean_worker.py`` in ``frozen-python`` source mode (the mode reviewed
production profiles require) with fixture admission, lets it run ``editor.py prepare`` on the
synthetic fixture, yields it via the facade and checks the verified checkpoint and full exit.
Fixture admission certifies no production RAM/CPU profile (see open-ocean PIPELINE-PROFILES).

  PYTHONPATH=<open-ocean checkout> python tests/e2e/ocean_gate.py \
      --python <venv python with locked runtime> --video-use <video-use checkout>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

from ocean_resources import (BACHFacade, CapacityReadback, Hold, HostLocalArbiter,
                             HostWriterAuthority, ResourceSocket, SlotRequest)
from ocean_resources.process import OwnedProcessExecutor, ProcessCommand

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from ai_media_editor.ocean_worker import job_id, valid_checkpoint  # noqa: E402

WORKER = REPO / "ai_media_editor" / "ocean_worker.py"
FIXTURE = REPO / "tests" / "e2e" / "fixture" / "fixture.mp4"
HOST = "ame-gate-host"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", required=True)
    ap.add_argument("--video-use", required=True)
    ap.add_argument("--model", default="large-v3")
    args = ap.parse_args()
    tmp = Path(tempfile.mkdtemp(prefix="ame-ocean-")).resolve()
    home, state = tmp / "home", tmp / "state"
    (home / "config").mkdir(parents=True)
    state.mkdir()
    (home / "config" / "settings.json").write_text(json.dumps({
        "compute": {"prefer": "local", "fallback": "local"}, "mac": {},
        "engines": {"single_speaker": "faster", "multi_speaker": "faster"},
        "models": {"faster_local": args.model}, "language": "en",
        "paths": {"venv_python": args.python, "video_use": args.video_use},
    }), encoding="utf-8")
    job = [args.python, str(REPO / "editor.py"), "prepare", str(FIXTURE), "--mode", "3", "--project", "ocean"]
    executable = Path(sys.executable).resolve()
    env = tuple((k, os.environ[k]) for k in ("PATH", "HOME", "SystemRoot", "TEMP", "TMP") if k in os.environ)
    command = ProcessCommand((str(executable), str(WORKER), "--", *job), REPO,
                             ((executable, sha256(executable)), (WORKER, sha256(WORKER))),
                             env + (("AI_MEDIA_EDITOR_HOME", str(home)),), source_mode="frozen-python")
    sequence = 0

    def capacity():
        nonlocal sequence
        sequence += 1
        return CapacityReadback(HOST, sequence, time.monotonic(), 128, 2, True, True)

    started = time.monotonic()
    with HostWriterAuthority(state, HOST) as writer:
        arbiter = HostLocalArbiter(writer, (ResourceSocket("compute", HOST, 64, 1, "fixture"),), capacity,
                                   time.monotonic, fixture_profiles=frozenset({"fixture"}), heartbeat_ttl=600)
        executor = OwnedProcessExecutor(arbiter, command, state, lambda p: valid_checkpoint(p, job_id(job)),
                                        timeout_seconds=30)
        facade = BACHFacade(arbiter, {"compute": executor.adapter()})
        try:
            arbiter.submit(SlotRequest("media-3b", "compute", "compute-slot", HOST, "media-3b-key"))
            grant = facade.start_next()
            for _ in range(20):  # the worker answers once the job child has exited
                try:
                    checkpoint = facade.yield_active(grant, requeue=False)
                    break
                except Hold:
                    time.sleep(5)
            else:
                raise SystemExit("GATE_FAIL: no verified checkpoint")
            payload = json.loads(checkpoint.payload_json)
            exited = all(run.exited and run.child.poll() is not None for run in executor._executions.values())
        finally:
            executor.close()
    takes = home / "projects" / "ocean" / "edit" / "takes_packed.md"
    checks = {"checkpoint_exit_0": payload["exit_code"] == 0, "owned_tree_exited": exited,
              "takes_packed": takes.is_file() and takes.stat().st_size > 0, "torch_released": arbiter.status()["torch"] is None}
    ok = all(checks.values())
    print(json.dumps({"gate": "ocean-3b", "pass": ok, "seconds": round(time.monotonic() - started, 1),
                      "checks": checks, "payload": payload}))
    print("GATE_OK" if ok else "GATE_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
