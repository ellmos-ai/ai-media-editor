"""Packaging regression tests (T-20260927-253152857).

Before this fix, `pip install [-e] .` failed outright with a setuptools
"Multiple top-level packages discovered in a flat-layout" error -- there was
no __init__.py anywhere and no explicit packages.find configuration, so the
storyboard extra (pip install -e ".[storyboard]") could never be exercised.
These tests guard the three things that made it installable again: the
console script declaration, the explicit package list, and that stt/tools
are now real importable packages.
"""

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
    assert scripts["ai-media-editor"] == "editor:main"


def test_packages_find_is_explicit_not_automatic():
    pyproject = _load_pyproject()
    setuptools_cfg = pyproject["tool"]["setuptools"]
    assert setuptools_cfg["py-modules"] == ["editor"]

    find_cfg = pyproject["tool"]["setuptools"]["packages"]["find"]
    include = set(find_cfg["include"])
    assert include == {"stt*", "tools*"}


def test_stt_and_tools_are_real_packages():
    assert (ROOT / "stt" / "__init__.py").is_file()
    assert (ROOT / "tools" / "__init__.py").is_file()


def test_editor_module_importable_with_stt_tools_on_syspath():
    """editor.py's own sys.path.insert(HERE/"stt"), sys.path.insert(HERE/"tools")
    trick must keep working after packaging -- this is what doctor()/prepare()
    rely on at runtime, editable or not."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "editor.py"), "modes"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "Werbeclip" in result.stdout
