"""Repository metadata, documentation, manifest, and discoverability parity tests for ai-media-editor."""

import json
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
    pyproject_path = ROOT / "pyproject.toml"
    if tomllib is not None:
        with pyproject_path.open("rb") as handle:
            return tomllib.load(handle)
    # Basic fallback parser if tomllib is unavailable
    text = pyproject_path.read_text(encoding="utf-8")
    return {"raw": text}


def test_version_consistency():
    """Verify version consistency across VERSION, pyproject.toml, and ellmos-module.v2.json."""
    version_file = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert version_file == "0.2.0"

    pyproject = _load_pyproject()
    if "project" in pyproject:
        assert pyproject["project"]["version"] == "0.2.0"
    else:
        assert 'version = "0.2.0"' in pyproject["raw"]

    with (ROOT / "ellmos-module.v2.json").open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    assert manifest["version"] == "0.2.0"


def test_manifest_parity():
    """Verify that ellmos-module.v2.json specifies valid schema, repository, and visibility."""
    manifest_path = ROOT / "ellmos-module.v2.json"
    assert manifest_path.is_file(), "ellmos-module.v2.json must exist"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data.get("schema") == "ellmos.module.v2"
    assert data.get("id") == "ai-media-editor"
    assert data.get("visibility") == "public"
    assert "ellmos-ai/ai-media-editor" in data.get("source_of_truth", {}).get("repository", "")


def test_documentation_links_and_no_file_uris():
    """Verify that all markdown documentation files use portable links without local file:/// URIs."""
    doc_files = [
        "README.md",
        "README_de.md",
        "llms.txt",
        "SECURITY.md",
        "CHANGELOG.md",
        "TODO.md",
        "CLAUDE.md",
        "RELEASE_GATE.md",
    ]
    for filename in doc_files:
        doc_path = ROOT / filename
        if not doc_path.is_file():
            continue
        content = doc_path.read_text(encoding="utf-8")
        assert "file:///" not in content, f"Found local file:/// URI in {filename}"


def test_llms_txt_integrity():
    """Verify that llms.txt contains discovery metadata, version, current timestamp, and ecosystem links."""
    llms_path = ROOT / "llms.txt"
    assert llms_path.is_file()
    content = llms_path.read_text(encoding="utf-8")
    assert "Last-checked: 2026-09-09" in content
    assert "ellmos-ai/ai-media-editor" in content
    assert "open-bricks" in content


def test_readme_badges_and_parity():
    """Verify that README.md and README_de.md include language switchers, up-to-date badges, and ecosystem links."""
    for filename in ("README.md", "README_de.md"):
        content = (ROOT / filename).read_text(encoding="utf-8")
        assert "tests-56" in content or "tests-46" in content or "tests-passed" in content or "passing" in content
        assert "license-MIT" in content or "MIT" in content
        assert "python-3.10" in content
        assert "open--bricks" in content
        assert "ellmos--ai" in content


def test_pyproject_tooling_integrity():
    """Verify that pyproject.toml defines build, metadata, classifiers, URLs, and pytest/ruff configuration."""
    pyproject = _load_pyproject()
    if "project" in pyproject:
        project = pyproject.get("project", {})
        assert project.get("name") == "ai-media-editor"
        assert project.get("requires-python") == ">=3.10"
        classifiers = project.get("classifiers", [])
        assert "Programming Language :: Python :: 3.10" in classifiers
        assert "Programming Language :: Python :: 3.11" in classifiers
        assert "Programming Language :: Python :: 3.12" in classifiers
        assert "Programming Language :: Python :: 3.13" in classifiers
        assert "Operating System :: OS Independent" in classifiers
        urls = project.get("urls", {})
        assert "Homepage" in urls
        assert "Documentation" in urls
        assert "Repository" in urls
        assert "Issues" in urls
        assert "Changelog" in urls
        assert "Security" in urls
        assert urls.get("Parent Organization") == "https://github.com/ellmos-ai"
        assert urls.get("Umbrella Ecosystem") == "https://github.com/open-bricks"
        tool = pyproject.get("tool", {})
        assert "ruff" in tool
        assert "pytest" in tool
    else:
        raw = pyproject["raw"]
        assert 'name = "ai-media-editor"' in raw
        assert "Programming Language :: Python :: 3.13" in raw
        assert "Umbrella Ecosystem" in raw
        assert "Parent Organization" in raw


def test_ci_workflow_parity():
    """Verify that GitHub Actions CI workflow configures multi-OS, Python 3.10-3.13, ruff, concurrency, and compileall."""
    ci_file = ROOT / ".github" / "workflows" / "ci.yml"
    assert ci_file.is_file(), "ci.yml must exist"
    content = ci_file.read_text(encoding="utf-8")
    assert "actions/checkout@v4" in content
    assert "actions/setup-python@v5" in content
    assert "ubuntu-latest" in content
    assert "windows-latest" in content
    assert "macos-latest" in content
    assert "3.10" in content
    assert "3.13" in content
    assert "ruff check ." in content
    assert "concurrency:" in content
    assert "cancel-in-progress: true" in content
    assert "python -m compileall -q ." in content


def test_security_policy_bilingual_parity():
    """Verify that SECURITY.md provides bilingual English and German policies with official contacts and SLAs."""
    sec_file = ROOT / "SECURITY.md"
    assert sec_file.is_file(), "SECURITY.md must exist"
    content = sec_file.read_text(encoding="utf-8")
    assert "## English" in content
    assert "## Deutsch" in content
    assert "security@open-bricks.org" in content
    assert "security@ellmos.ai" in content
    assert "support@lukasgeiger.com" in content
    assert "lukas@open-bricks.org" in content
    assert "0.2.x" in content
    assert "48 hours" in content or "48 Stunden" in content
    assert "5 business days" in content or "5 Werktagen" in content
    assert "Local-First" in content or "local-first" in content.lower()
    assert "https://github.com/ellmos-ai/ai-media-editor/security/advisories" in content


def test_gitignore_hygiene():
    """Verify that .gitignore contains conflict copy, packaging smoke, and temp file patterns."""
    gi_path = ROOT / ".gitignore"
    assert gi_path.is_file()
    content = gi_path.read_text(encoding="utf-8")
    for pattern in ["*.sync-conflict-*", "*-CONFLIT-*", "wheelhouse/", ".wheel-smoke/", "*.tmp", "*.bak"]:
        assert pattern in content, f"Pattern {pattern} missing from .gitignore"


def test_cli_modes_smoke():
    """Verify that editor.py modes CLI command outputs all supported use cases."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "editor.py"), "modes"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    assert "Audio, 1 Sprecher" in result.stdout
    assert "Video (A+V)" in result.stdout
