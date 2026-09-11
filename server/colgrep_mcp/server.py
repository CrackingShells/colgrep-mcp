"""MCPServer instance and registration entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server import MCPServer
from mcp.server.mcpserver import Context

from . import __version__
from .adapter import ColgrepAdapter
from .config import Settings

INSTRUCTIONS = (
    "colgrep gives ranked semantic + keyword (hybrid) search over code units "
    "(functions, classes, docs sections). Use `search` for any question about what, where "
    "or how code does something instead of shell grep; add `pattern` (a regex) to narrow "
    "hybrid results when you know an identifier. Omit `limit` for an exhaustive listing; "
    "use 10-25 while exploring. Results carry `hit_id`s: call `expand` to read the source "
    "of the few hits that matter instead of opening whole files. On a large, never-indexed "
    "repository call `index_build` first; `index_status` tells you whether that is needed."
)



@dataclass
class AppContext:
    """Process-wide state owned by the lifespan: one settings object, one adapter."""

    settings: Settings
    adapter: ColgrepAdapter


@asynccontextmanager
async def lifespan(server: MCPServer) -> AsyncIterator[AppContext]:
    settings = Settings.from_env()
    adapter = ColgrepAdapter(binary=settings.binary, timeout_s=settings.timeout_s)
    yield AppContext(settings=settings, adapter=adapter)


mcp = MCPServer("colgrep", instructions=INSTRUCTIONS, version=__version__, lifespan=lifespan)


def get_app(ctx: Context) -> AppContext:
    return ctx.request_context.lifespan_context


def get_adapter(ctx: Context) -> ColgrepAdapter:
    return get_app(ctx).adapter


def get_settings(ctx: Context) -> Settings:
    return get_app(ctx).settings


def build() -> MCPServer:
    """Register every tool/resource/prompt module onto `mcp` and return it."""
    from . import prompts, resources, tools_index, tools_search

    tools_search.register(mcp)
    tools_index.register(mcp)
    resources.register(mcp)
    prompts.register(mcp)
    return mcp
