from __future__ import annotations

import json
import subprocess

import pytest
from mcp import Client

from colgrep_mcp import __version__
from colgrep_mcp.server import build


def test_fake_colgrep_emits_json(fake_colgrep_bin):
    out = subprocess.run([fake_colgrep_bin, "--json", "-k", "2", "config parsing", "."], capture_output=True, text=True, check=True)
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
