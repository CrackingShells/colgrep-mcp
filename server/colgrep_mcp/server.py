"""MCPServer instance and registration entry point."""

from __future__ import annotations

from mcp.server import MCPServer

from . import __version__

INSTRUCTIONS = (
    "colgrep gives ranked semantic + keyword (hybrid) search over code units "
    "(functions, classes, docs sections). Use `search` for any question about what, where "
    "or how code does something instead of shell grep; add `pattern` (a regex) to narrow "
    "hybrid results when you know an identifier. Omit `limit` for an exhaustive listing; "
    "use 10-25 while exploring. Results carry `hit_id`s: call `expand` to read the source "
    "of the few hits that matter instead of opening whole files. On a large, never-indexed "
    "repository call `index_build` first; `index_status` tells you whether that is needed."
)

mcp = MCPServer("colgrep", instructions=INSTRUCTIONS, version=__version__)


def build() -> MCPServer:
    """Register every tool/resource/prompt module onto `mcp` and return it."""
    from . import prompts, resources, tools_index, tools_search

    tools_search.register(mcp)
    tools_index.register(mcp)
    resources.register(mcp)
    prompts.register(mcp)
    return mcp
