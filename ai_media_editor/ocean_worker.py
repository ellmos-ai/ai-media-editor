"""Open Ocean owned-process worker (protocol ``ocean-owned-process.v1``) for pipeline 3b.

Shim between open-ocean's ``OwnedProcessExecutor`` and one pinned ai-media-editor job.
Stdlib only and below 8 KiB, so it also runs as a ``frozen-python`` command (``-I -S``)::

    <python> ocean_worker.py -- <venv python> <repo>/editor.py prepare <media> --mode 3 --project p
    <python> ocean_worker.py -- <venv python> <video-use>/helpers/render.py <edl.json> -o final.mp4

The argv after ``--`` runs as one child inside the owned process tree. A checkpoint request is
answered at the next application-safe point, i.e. once that child has exited, with the payload
``{"job": sha256(argv), "exit_code": int}``. A resumed execution whose verified predecessor
already finished the same job with exit code 0 does not run it again. Pass
``valid_checkpoint(payload, job_id(argv))`` to the executor as the application validator.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

PROTOCOL = "ocean-owned-process.v1"


def job_id(argv: list[str]) -> str:
    return hashlib.sha256(json.dumps(list(argv)).encode("utf-8")).hexdigest()


def valid_checkpoint(payload: object, job: str) -> bool:
    return (
        isinstance(payload, dict)
        and set(payload) == {"job", "exit_code"}
        and payload["job"] == job
        and type(payload["exit_code"]) is int
    )


def _read(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write(root: Path, name: str, value: dict) -> None:
    tmp = root / (name + ".tmp")
    tmp.write_text(json.dumps(value), encoding="utf-8")
    tmp.replace(root / name)


def main(argv: list[str]) -> int:
    if "--" not in argv or argv.index("--") == len(argv) - 1:
        print("usage: ocean_worker.py -- <job argv...>", file=sys.stderr)
        return 2
    job_argv = argv[argv.index("--") + 1:]
    home = os.environ.get("AI_MEDIA_EDITOR_HOME")
    settings = _read(Path(home) / "config" / "settings.json") if home else None
    if isinstance(settings, dict) and settings.get("compute", {}).get("prefer") != "local":
        # PIPELINE-EXECUTOR: remote workers need their own lifecycle/residency adapter.
        print("ocean_worker: compute.prefer must be 'local' inside an owned process", file=sys.stderr)
        return 2
    root = Path(os.environ["OCEAN_RESOURCE_RUN_DIR"])
    start = _read(root / "start.json")
    if not isinstance(start, dict) or start.get("schema") != PROTOCOL:
        print("ocean_worker: invalid start.json", file=sys.stderr)
        return 2
    identity = {key: start[key] for key in ("schema", "grant", "execution_identity")}
    job = job_id(job_argv)
    resume = start.get("resume")
    child = None
    if valid_checkpoint(resume, job) and resume["exit_code"] == 0:
        payload = resume
    else:
        payload = None
        with (root / "job.log").open("ab") as log:
            # Same process group/job on purpose: a new session would escape the owned tree.
            child = subprocess.Popen(job_argv, stdin=subprocess.DEVNULL, stdout=log,
                                     stderr=subprocess.STDOUT)
    _write(root, "ready.json", identity)
    # ponytail: no preemption mid-job (killing the child would leave its ffmpeg grandchildren
    # running); the owner's bounded checkpoint wait holds until the job ends. Add phase-level
    # checkpoints if single jobs grow beyond the yield latency an interactive slot can accept.
    while True:
        if payload is None and child.poll() is not None:
            payload = {"job": job, "exit_code": child.returncode}
        if payload is not None and _read(root / "checkpoint.request.json") == identity:
            _write(root, "checkpoint.json", {**identity, "payload": payload, "quiescent": True})
            break
        time.sleep(0.1)
    while True:  # stay quiescent until the owner stops the process tree
        time.sleep(1)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
