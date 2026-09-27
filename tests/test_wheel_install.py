"""Exercise the installed wheel without importing code from the checkout."""

import os
import subprocess
import sys
import venv
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DATA_SUFFIXES = {".cjs", ".cmd", ".ps1", ".vbs"}


def test_wheel_install_and_modes(tmp_path):
    wheel_dir = tmp_path / "wheels"
    wheel_dir.mkdir()
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-w", str(wheel_dir)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
    )

    (wheel,) = wheel_dir.glob("*.whl")
    with zipfile.ZipFile(wheel) as archive:
        packaged_suffixes = {
            Path(name).suffix
            for name in archive.namelist()
            if name.startswith("ai_media_editor/tools/")
        }
    assert PACKAGE_DATA_SUFFIXES <= packaged_suffixes

    environment = tmp_path / "venv"
    venv.EnvBuilder(with_pip=True).create(environment)
    scripts_dir = environment / ("Scripts" if os.name == "nt" else "bin")
    python = scripts_dir / ("python.exe" if os.name == "nt" else "python")
    command = scripts_dir / ("ai-media-editor.exe" if os.name == "nt" else "ai-media-editor")
    subprocess.run(
        [str(python), "-m", "pip", "install", "--no-deps", str(wheel)],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )

    workdir = tmp_path / "outside-checkout"
    workdir.mkdir()
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["AI_MEDIA_EDITOR_HOME"] = str(tmp_path / "home")
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [str(command), "modes"],
        cwd=workdir,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "Werbeclip" in result.stdout
