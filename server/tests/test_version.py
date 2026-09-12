"""Guards that the version lives in exactly one place: `server/pyproject.toml`.

`colgrep_mcp.__version__` is derived from installed package metadata (see
`colgrep_mcp/__init__.py`); the plugin manifests and the `uvx
colgrep-mcp==<version>` pin in the three MCP manifests are rewritten by
`cz bump` through `version_files` (pypi_publication R01 §C6). Nothing else
enforces that they stay aligned except this test and
`tests/test_manifests.py`.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import colgrep_mcp

# server/tests/test_version.py -> parents[0]=tests, [1]=server, [2]=repo root
SERVER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVER_ROOT.parent


def _pyproject_version() -> str:
    data = tomllib.loads((SERVER_ROOT / "pyproject.toml").read_text())
    return data["project"]["version"]


def test_version_matches_pyproject():
    assert colgrep_mcp.__version__ == _pyproject_version()


def test_manifests_match_pyproject():
    version = _pyproject_version()

    for relpath in ("plugin.json", ".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
        manifest = json.loads((REPO_ROOT / relpath).read_text())
        assert manifest["version"] == version, f"{relpath} version mismatch"


def test_mcp_manifests_pin_the_pyproject_version():
    """The `colgrep-mcp==` regex in `version_files` must have rewritten every pin; a lag means a hand edit."""
    version = _pyproject_version()

    for relpath in (".claude-plugin/mcp.json", ".codex-plugin/mcp.json", "mcp.json"):
        server = json.loads((REPO_ROOT / relpath).read_text())["mcpServers"]["colgrep"]
        assert server["args"] == [f"colgrep-mcp=={version}"], f"{relpath} pin mismatch"


def test_uv_lock_records_the_pyproject_version():
    """`cz bump` re-locks via `pre_bump_hooks` and stages uv.lock; a mismatch means a bump was done by hand."""
    lock = tomllib.loads((SERVER_ROOT / "uv.lock").read_text())
    ours = [pkg for pkg in lock["package"] if pkg["name"] == "colgrep-mcp"]
    assert len(ours) == 1
    assert ours[0]["version"] == _pyproject_version()
