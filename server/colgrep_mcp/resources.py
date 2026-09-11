"""Resources: the packaged guide, live settings/indexes, and per-path status.

R02 §Resources and completions (adopt-guarded: every fact served here is also
reachable through a tool, so a client without resource support loses nothing).

Static resources (`colgrep://guide`, `colgrep://settings`, `colgrep://indexes`)
have no URI template variables, and the SDK's `@mcp.resource` decorator refuses
a `Context` parameter on a static resource — there is nowhere for
`ResourceManager.get_resource` to obtain a request `Context` to inject (see
`mcp.server.mcpserver.server.MCPServer.resource`). Only the `colgrep://status/{+path}`
template can take `ctx: Context` and reuse the lifespan's shared adapter via
`get_adapter`. The two plain-JSON static resources instead build a short-lived
adapter straight from `Settings.from_env()`, exactly as `server.lifespan` does.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context, ResourceSecurity
from mcp.server.mcpserver.exceptions import ResourceError

from .adapter import ColgrepAdapter, ColgrepError
from .config import Settings
from .errors import HINTS, Code, from_adapter_error
from .models import IndexList
from .server import get_adapter


def _standalone_adapter() -> ColgrepAdapter:
    """Build an adapter from the environment, for handlers with no request `Context`."""
    settings = Settings.from_env()
    return ColgrepAdapter(binary=settings.binary, timeout_s=settings.timeout_s)


def _map_adapter_error(exc: ColgrepError) -> ResourceError:
    """Same coded `[CODE] ... Next: ...` wording the tool layer uses (`errors.from_adapter_error`)."""
    return ResourceError(str(from_adapter_error(exc)))


def _normalize_status_path(path: str) -> Path:
    """Accept `path` with or without a leading `/` and return an absolute `Path`.

    `{+path}` keeps inner slashes; the client may reasonably supply either
    `colgrep://status/Users/x/proj` or `colgrep://status//Users/x/proj`.
    """
    if not path.startswith("/"):
        path = "/" + path
    return Path(path)


def guide() -> str:
    """`colgrep://guide` — the packaged usage guide, verbatim."""
    return importlib.resources.files("colgrep_mcp").joinpath("guide.md").read_text()


async def settings_resource() -> dict[str, str]:
    """`colgrep://settings` — parsed `colgrep settings`."""
    adapter = _standalone_adapter()
    try:
        return await adapter.settings()
    except ColgrepError as exc:
        raise _map_adapter_error(exc) from exc


async def indexes_resource() -> dict[str, Any]:
    """`colgrep://indexes` — every indexed project on this machine (`IndexList`)."""
    adapter = _standalone_adapter()
    try:
        infos = await adapter.stats()
    except ColgrepError as exc:
        raise _map_adapter_error(exc) from exc
    return IndexList(indexes=infos).model_dump()


async def status_resource(path: str, ctx: Context) -> dict[str, Any]:
    """`colgrep://status/{+path}` — `IndexStatus` for the given absolute path."""
    resolved = _normalize_status_path(path)
    adapter = get_adapter(ctx)
    try:
        status = await adapter.status(resolved)
    except ColgrepError as exc:
        raise _map_adapter_error(exc) from exc
    return status.model_dump()


def errors_resource() -> str:
    """`colgrep://errors` — every coded failure/degradation and its hint, rendered from `HINTS`.

    An agent that only ever sees the `[CODE]` prefix (a `ToolError` message or
    a `SearchResult` note) can look the code up here for the full "next
    usage pattern" sentence without re-reading `guide.md` end to end.
    """
    lines = [
        "# colgrep-mcp error and hint codes",
        "",
        "Every `ToolError` this server raises starts with one of these codes and",
        "ends with `Next: <hint>`; every degraded-success note in `SearchResult.notes`",
        "starts with one too.",
        "",
        "| Code | Hint |",
        "|:--|:--|",
    ]
    lines += [f"| `{code}` | {HINTS[code]} |" for code in Code]
    return "\n".join(lines) + "\n"


def register(mcp: MCPServer) -> None:
    """Attach this module's handlers to the server."""
    mcp.resource("colgrep://guide", mime_type="text/markdown", title="colgrep usage guide")(guide)
    mcp.resource("colgrep://settings", mime_type="application/json")(settings_resource)
    mcp.resource("colgrep://indexes", mime_type="application/json")(indexes_resource)
    mcp.resource(
        "colgrep://status/{+path}",
        mime_type="application/json",
        security=ResourceSecurity(
            reject_path_traversal=True, reject_absolute_paths=False, reject_null_bytes=True
        ),
    )(status_resource)
    mcp.resource("colgrep://errors", mime_type="text/markdown", title="colgrep-mcp error and hint codes")(
        errors_resource
    )
