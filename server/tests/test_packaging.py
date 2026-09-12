"""Drift guards for what the PyPI distribution carries (pypi_publication R01 §C5).

hatchling includes only files under `server/`, and ignores a
`license-files = ["../LICENSE"]` glob without any error (probed 2026-09-12:
no `License-File` in METADATA). The AGPL requires its text to travel with
every distribution, so `server/LICENSE` is a byte copy of the repository
`LICENSE`; this test is the only thing that keeps the two identical.
"""

from __future__ import annotations

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
