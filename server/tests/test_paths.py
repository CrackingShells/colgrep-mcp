from __future__ import annotations

from pathlib import Path

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from colgrep_mcp.config import Settings
from colgrep_mcp.paths import default_root, resolve_paths


def test_default_root_prefers_env(tmp_path):
    root, src = default_root(Settings(root=tmp_path), [Path("/elsewhere")])
    assert root == tmp_path.resolve() and src == "env"


def test_default_root_falls_back_to_roots_then_cwd(tmp_path):
    root, src = default_root(Settings(), [tmp_path])
    assert root == tmp_path.resolve() and src == "roots"
    root, src = default_root(Settings(), None)
    assert root == Path.cwd().resolve() and src == "cwd"


def test_resolve_relative_against_root(tmp_path):
    (tmp_path / "src").mkdir()
    assert resolve_paths(["src"], Settings(root=tmp_path), None) == [(tmp_path / "src").resolve()]


def test_resolve_missing_lists_paths(tmp_path):
    with pytest.raises(ToolError) as e:
        resolve_paths(["nope", "also_nope"], Settings(root=tmp_path), None)
    assert "nope, also_nope" in str(e.value)


def test_resolve_empty_returns_root(tmp_path):
    assert resolve_paths(None, Settings(root=tmp_path), None) == [tmp_path.resolve()]
