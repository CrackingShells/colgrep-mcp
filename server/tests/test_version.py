"""Guards that the version lives in exactly one place: `server/pyproject.toml`.

`colgrep_mcp.__version__` is derived from installed package metadata (see
`colgrep_mcp/__init__.py`), and the three plugin manifests mirror the
pyproject version by hand until a release bumps them all together. Nothing
else enforces that they stay aligned except this test and
`tests/test_manifests.py` (owned by the sibling `launcher` leaf, not edited
here).
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


def test_uv_lock_records_the_pyproject_version():
    """`cz bump` re-locks via `pre_bump_hooks` and stages uv.lock; a mismatch means a bump was done by hand."""
    lock = tomllib.loads((SERVER_ROOT / "uv.lock").read_text())
    ours = [pkg for pkg in lock["package"] if pkg["name"] == "colgrep-mcp"]
    assert len(ours) == 1
    assert ours[0]["version"] == _pyproject_version()
