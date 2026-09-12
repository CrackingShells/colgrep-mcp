"""Stdio round-trip test (R01 server assembly).

Everything else in the suite drives the server in-process via `Client(build())`
(`InMemoryTransport`) — fast, but it never proves the console script itself
starts, that `--transport stdio` is wired to a real subprocess, or that stdout
carries nothing but the JSON-RPC protocol. This module spawns the actual
`python -m colgrep_mcp` entry point (what `colgrep-mcp` resolves to) as a
subprocess and drives it over stdin/stdout with the SDK's real stdio
transport.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import anyio
import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters, stdio_client

pytestmark = pytest.mark.anyio

# server/tests/test_stdio.py -> server/
SERVER_DIR = Path(__file__).resolve().parent.parent


def _stdio_params(fake_colgrep_bin: str, root: Path, extra_env: dict[str, str] | None = None) -> StdioServerParameters:
    """`StdioServerParameters` for `sys.executable -m colgrep_mcp`, cwd=server/.

    Only `COLGREP_MCP_BINARY`/`COLGREP_MCP_ROOT` (and any `extra_env`) are
    passed as extra env — `stdio_client` merges these over a minimal
    inherited environment (`HOME`, `PATH`, ... — see
    `mcp.client.stdio.get_default_environment`), it does not inherit the
    parent process's full environment.
    """
    env = {"COLGREP_MCP_BINARY": fake_colgrep_bin, "COLGREP_MCP_ROOT": str(root)}
    env.update(extra_env or {})
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "colgrep_mcp"],
        env=env,
        cwd=str(SERVER_DIR),
    )


async def test_stdio_round_trip(fake_colgrep_bin, tmp_path):
    """Spawn the real console entry point over stdio and drive a full session.

    Never against the real `colgrep` binary or under `/private/tmp` — this
    uses `fake_colgrep.py` and pytest's own `tmp_path`, never the repository
    checkout, as the project root.
    """
    params = _stdio_params(fake_colgrep_bin, tmp_path)

    with anyio.fail_after(60):
        async with Client(params, raise_exceptions=True) as client:
            assert client.server_info.name == "colgrep"

            tools = await client.list_tools()
            assert len(tools.tools) == 8

            resources = await client.list_resources()
            # 3 today (guide, settings, indexes); a fourth (colgrep://errors) is
            # landing in parallel from another leaf, so this asserts a floor.
            assert len(resources.resources) >= 3

            templates = await client.list_resource_templates()
            assert len(templates.resource_templates) == 1

            prompts = await client.list_prompts()
            assert len(prompts.prompts) == 3

            result = await client.call_tool("search", {"query": "config parsing"})
            assert result.is_error is False
            assert result.structured_content["total"] > 0
            assert len(result.structured_content["hits"]) > 0


async def test_stdio_stderr_has_no_deprecation_warning(fake_colgrep_bin, tmp_path):
    """A `search` call must not leak `MCPDeprecationWarning` onto stderr.

    `logging_utils.safe_log` forwards tool-side log lines to the client via
    `ctx.info`/`ctx.warning` — convenience methods deprecated as of 2026-07-28
    (SEP-2577) that the SDK warns about at runtime on every call. Without
    `__main__.main`'s `warnings.filterwarnings`, that warning text would land
    on stderr indistinguishable from a real problem. `search`'s own
    `render_search_text` truncation path (`tools_search._do_search` /
    `search`) calls `safe_log(ctx, "warning", ...)` once text is capped, so a
    fixture large enough to force truncation reliably exercises the
    deprecated path instead of depending on colgrep happening to write to
    stderr. Capturing this needs a real OS-level file for `stdio_client`'s
    `errlog` (a Python buffer has no file descriptor to redirect the
    subprocess's stderr into) — not `Client(StdioServerParameters(...))`,
    which does not expose `errlog`, but `Client` wrapping `stdio_client(...)`
    directly still satisfies "a stdio transport form" per the SDK's own
    `Client` docstring (`server: ... | Transport | StdioServerParameters | str`).
    """
    hits = [
        {
            "unit": {
                "name": f"unit_{i}",
                "qualified_name": f"mod{i}.py::unit_{i}",
                "file": f"/tmp/fake-corpus/mod{i}.py",
                "line": 1,
                "end_line": 2,
                "language": "python",
                "unit_type": "function",
                "signature": f"def unit_{i}()",
                "code": f"def unit_{i}():\n    return {i}\n",
            },
            "score": round(1.0 - i * 0.0001, 6),
        }
        for i in range(2000)
    ]
    fixture_path = tmp_path / "hits_large.json"
    fixture_path.write_text(json.dumps(hits))

    params = _stdio_params(
        fake_colgrep_bin,
        tmp_path,
        extra_env={"FAKE_COLGREP_HITS": str(fixture_path), "COLGREP_MCP_TEXT_BUDGET": "3000"},
    )
    stderr_path = tmp_path / "stderr.log"

    with anyio.fail_after(60):
        with open(stderr_path, "w", encoding="utf-8") as errlog:
            async with Client(stdio_client(params, errlog=errlog), raise_exceptions=True) as client:
                result = await client.call_tool("search", {"query": "x", "limit": None, "pattern": "unit_"})
                assert result.is_error is False
                assert result.structured_content["truncated"] is True  # proves the warning-log path ran

    stderr_text = stderr_path.read_text()
    assert "MCPDeprecationWarning" not in stderr_text
    assert "colgrep-mcp" in stderr_text  # the startup INFO log line landed on stderr, not stdout
