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


# --- resolve_target_paths: when client roots are worth a round-trip ----------


def test_roots_can_matter_only_without_env_root_and_with_something_relative(tmp_path):
    from colgrep_mcp.paths import _roots_can_matter

    # env root set: never (the plugin always sets COLGREP_MCP_ROOT).
    assert _roots_can_matter(None, Settings(root=tmp_path)) is False
    assert _roots_can_matter(["rel"], Settings(root=tmp_path)) is False
    # no env root: only when a default root would actually be used.
    assert _roots_can_matter(None, Settings()) is True
    assert _roots_can_matter(["rel/path"], Settings()) is True
    assert _roots_can_matter([str(tmp_path)], Settings()) is False


@pytest.mark.anyio
async def test_client_roots_decodes_file_uris(tmp_path):
    """A client root is a `file:` URI: percent-encoding is decoded and (on
    Windows) the `/C:/...` URI form becomes a drive-rooted path, so the
    result equals what `Path.as_uri()` started from."""
    from types import SimpleNamespace

    from mcp.types import ListRootsResult, Root

    from colgrep_mcp.paths import client_roots

    spaced = tmp_path / "a b"
    spaced.mkdir()

    async def list_roots():
        return ListRootsResult(roots=[Root(uri=spaced.as_uri())])

    ctx = SimpleNamespace(session=SimpleNamespace(list_roots=list_roots))
    assert await client_roots(ctx) == [spaced]
