"""MCPServer instance and registration entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.types import ToolAnnotations

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


#: Annotations shared by every read-only tool (`search`, `find_files`, `expand`,
#: `index_status`, `list_indexes`, `doctor`): they neither mutate nor reach
#: outside the machine, and repeating a call is harmless.
READ_ONLY_TOOL = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False)


@dataclass
class AppContext:
    """Process-wide state owned by the lifespan: one settings object, one adapter."""

    settings: Settings
    adapter: ColgrepAdapter


#: The running server's `AppContext`, set for the lifespan's duration so
#: handlers the SDK gives no request `Context` (static resources, the
#: completion callback) still share the one adapter instead of building
#: their own from the environment on every call.
_app: AppContext | None = None


@asynccontextmanager
async def lifespan(server: MCPServer) -> AsyncIterator[AppContext]:
    global _app
    settings = Settings.from_env()
    adapter = ColgrepAdapter(binary=settings.binary, timeout_s=settings.timeout_s)
    _app = AppContext(settings=settings, adapter=adapter)
    try:
        yield _app
    finally:
        _app = None


mcp = MCPServer("colgrep", instructions=INSTRUCTIONS, version=__version__, lifespan=lifespan)


def get_app(ctx: Context | None = None) -> AppContext:
    """The process-wide `AppContext`: from the request when `ctx` is given, else the lifespan's.

    Raises `RuntimeError` when called outside a running server (no lifespan
    has set the handle) — a programming error, never a client-visible state.
    """
    if ctx is not None:
        return ctx.request_context.lifespan_context
    if _app is None:
        raise RuntimeError("colgrep-mcp server is not running: no lifespan context available")
    return _app


def get_adapter(ctx: Context | None = None) -> ColgrepAdapter:
    return get_app(ctx).adapter


def get_settings(ctx: Context | None = None) -> Settings:
    return get_app(ctx).settings


def build() -> MCPServer:
    """Register every tool/resource/prompt module onto `mcp` and return it."""
    from . import prompts, resources, tools_index, tools_search

    tools_search.register(mcp)
    tools_index.register(mcp)
    resources.register(mcp)
    prompts.register(mcp)
    return mcp
