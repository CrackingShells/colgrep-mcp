"""Drift guards for what the PyPI distribution carries (pypi_publication R01 §C5).

hatchling includes only files under `server/`, and ignores a
`license-files = ["../LICENSE"]` glob without any error (probed 2026-09-12:
no `License-File` in METADATA). The AGPL requires its text to travel with
every distribution, so `server/LICENSE` is a byte copy of the repository
`LICENSE`; this test is the only thing that keeps the two identical.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVER_ROOT.parent


def test_server_license_is_a_copy_of_the_repository_license():
    assert (SERVER_ROOT / "LICENSE").read_bytes() == (REPO_ROOT / "LICENSE").read_bytes()


def test_project_urls_point_at_the_repository():
    """PyPI's sidebar is built from `[project.urls]`; the manifests already carry the same repository URL."""
    project = tomllib.loads((SERVER_ROOT / "pyproject.toml").read_text())["project"]
    urls = project["urls"]
    assert set(urls) >= {"Homepage", "Repository", "Changelog", "Issues"}
    assert all(url.startswith("https://github.com/CrackingShells/colgrep-mcp") for url in urls.values())
    assert project["readme"] == "README.md"


# A path from a maintainer's machine — a home directory other than the
# `/Users/me` placeholder, a `~/Documents/...` tree, a Claude scratchpad, an
# encoded project directory — once reached PyPI inside a fixture and sat in
# public reports for four campaigns. Every one was rewritten to a placeholder
# on 2026-09-13; this guard keeps the next one out.
_LOCAL_PATH_RE = re.compile(
    r"/Users/(?!(?:me|x|name)/)[^/\s`\"']+/|/Users/me/Documents/|~/Documents/|claude-501|-Users-(?!me-)[A-Za-z]"
)
_SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "dist", "build", "node_modules"}


def _tracked_text_files():
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or _SKIP_DIRS & set(path.relative_to(REPO_ROOT).parts):
            continue
        try:
            yield path, path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue


def test_no_local_machine_paths_anywhere_in_the_repository():
    offenders = [
        f"{path.relative_to(REPO_ROOT)}:{lineno}"
        for path, text in _tracked_text_files()
        if path != Path(__file__)
        for lineno, line in enumerate(text.splitlines(), 1)
        if _LOCAL_PATH_RE.search(line)
    ]
    assert not offenders, f"local machine paths leaked into: {offenders[:10]}"
