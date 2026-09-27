"""Regression tests for the installable :mod:`ai_media_editor` namespace."""

import os
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 fallback
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None

ROOT = Path(__file__).resolve().parents[1]


def _load_pyproject():
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def test_console_script_declared():
    pyproject = _load_pyproject()
    scripts = pyproject["project"]["scripts"]
    assert scripts["ai-media-editor"] == "ai_media_editor.editor:main"


def test_packages_find_is_explicit_not_automatic():
    pyproject = _load_pyproject()
    setuptools_cfg = pyproject["tool"]["setuptools"]
    assert "py-modules" not in setuptools_cfg

    find_cfg = pyproject["tool"]["setuptools"]["packages"]["find"]
    include = set(find_cfg["include"])
    assert include == {"ai_media_editor*"}

    package_data = setuptools_cfg["package-data"]["ai_media_editor.tools"]
    assert set(package_data) == {"*.cjs", "*.cmd", "*.ps1", "*.vbs"}


def test_namespace_contains_stt_and_tools_packages_only():
    package = ROOT / "ai_media_editor"
    assert (package / "__init__.py").is_file()
    assert (package / "editor.py").is_file()
    assert (package / "stt" / "__init__.py").is_file()
    assert (package / "tools" / "__init__.py").is_file()
    assert not (ROOT / "stt").exists()
    assert not (ROOT / "tools").exists()


def test_root_compatibility_shim_runs_without_install():
    """The documented root script remains available without an install."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "editor.py"), "modes"],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "Werbeclip" in result.stdout
