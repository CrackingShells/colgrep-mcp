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


@pytest.mark.anyio
async def test_overlapping_sessions_keep_their_own_app_handle(settings_env):
    """Two servers whose lifespans overlap in one process must not share the
    ctx-less app handle (review OV1): the first to exit used to clear a module
    global out from under the second, whose static resources then failed with
    `RuntimeError`. A `ContextVar` scopes the handle to each lifespan's task tree."""
    import asyncio

    started = asyncio.Event()
    release = asyncio.Event()

    async def short_lived():
        async with Client(build(), raise_exceptions=True):
            started.set()
        release.set()

    async def long_lived():
        async with Client(build(), raise_exceptions=True) as c:
            await started.wait()
            await release.wait()  # the other session has fully exited by now
            # `colgrep://indexes` reaches the adapter through the ctx-less handle.
            r = await c.read_resource("colgrep://indexes")
            assert r.contents and "indexes" in r.contents[0].text

    await asyncio.gather(short_lived(), long_lived())
