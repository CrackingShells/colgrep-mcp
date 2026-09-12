"""MCPServer instance and registration entry point.

The only module holding the process-wide app handle: `get_app`/`get_adapter`/
`get_settings` are the one way to reach the lifespan's single `Settings` and
single `ColgrepAdapter`, and `READ_ONLY_TOOL` is defined once here for every
read-only tool registration (R01 §C1).
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar
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
#: their own from the environment on every call. A `ContextVar`, not a
#: module global: every request task the SDK spawns descends from the task
#: that entered the lifespan and so inherits its value, while two servers
#: whose lifespans overlap in one process (the test suite's in-memory
#: clients can do this) each see only their own (review OV1).
_app_var: ContextVar[AppContext | None] = ContextVar("colgrep_mcp_app", default=None)


@asynccontextmanager
async def lifespan(server: MCPServer) -> AsyncIterator[AppContext]:
    settings = Settings.from_env()
    adapter = ColgrepAdapter(binary=settings.binary, timeout_s=settings.timeout_s)
    app = AppContext(settings=settings, adapter=adapter)
    token = _app_var.set(app)
    try:
        yield app
    finally:
        _app_var.reset(token)


mcp = MCPServer("colgrep", instructions=INSTRUCTIONS, version=__version__, lifespan=lifespan)


def get_app(ctx: Context | None = None) -> AppContext:
    """The process-wide `AppContext`: from the request when `ctx` is given, else the lifespan's.

    Raises `RuntimeError` when called outside a running server (no lifespan
    has set the handle) — a programming error, never a client-visible state.
    """
    if ctx is not None:
        return ctx.request_context.lifespan_context
    app = _app_var.get()
    if app is None:
        raise RuntimeError("colgrep-mcp server is not running: no lifespan context available")
    return app


def get_adapter(ctx: Context | None = None) -> ColgrepAdapter:
    return get_app(ctx).adapter


def get_settings(ctx: Context | None = None) -> Settings:
    return get_app(ctx).settings


def register_tool(
    server: MCPServer, handler: Callable[..., object], *, title: str, annotations: ToolAnnotations
) -> None:
    """Register `handler` as a tool whose description is its docstring, dedented.

    The SDK takes `handler.__doc__` verbatim, so a multi-line docstring's
    indentation (and its trailing newline-plus-spaces) would be shipped to
    every client on every `tools/list`. `inspect.getdoc` strips exactly that
    and nothing else; the words the model reads are unchanged.
    """
    server.tool(title=title, description=inspect.getdoc(handler), annotations=annotations)(handler)


def build() -> MCPServer:
    """Register every tool/resource/prompt module onto `mcp` and return it."""
    from . import prompts, resources, tools_index, tools_search

    tools_search.register(mcp)
    tools_index.register(mcp)
    resources.register(mcp)
    prompts.register(mcp)
    return mcp
