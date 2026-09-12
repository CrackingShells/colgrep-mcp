from __future__ import annotations

import json
import subprocess

import pytest
from mcp import Client

from colgrep_mcp import __version__
from colgrep_mcp.server import build


def test_fake_colgrep_emits_json(fake_colgrep_bin):
    out = subprocess.run(
        [fake_colgrep_bin, "--json", "-k", "2", "config parsing", "."],
        capture_output=True,
        text=True,
        check=True,
    )
    hits = json.loads(out.stdout)
    assert len(hits) == 2
    assert {"unit", "score"} <= hits[0].keys()


@pytest.mark.anyio
async def test_server_initializes(settings_env):
    async with Client(build(), raise_exceptions=True) as client:
        assert client.server_info.name == "colgrep"
        assert client.server_info.version == __version__
        tools = await client.list_tools()
        assert isinstance(tools.tools, list)


@pytest.mark.anyio
async def test_tool_descriptions_are_dedented(settings_env):
    """`register_tool` ships docstrings through `inspect.getdoc`: no line of any
    tool description starts with indentation and none ends in trailing
    whitespace — bytes every client would otherwise receive on every
    `tools/list`."""
    async with Client(build(), raise_exceptions=True) as c:
        tools = (await c.list_tools()).tools
    assert tools
    for tool in tools:
        desc = tool.description or ""
        assert desc == desc.strip(), tool.name
        assert not any(line.startswith((" ", "\t")) for line in desc.splitlines()), tool.name
