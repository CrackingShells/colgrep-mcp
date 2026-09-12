"""Resources: the packaged guide, live settings/indexes, and per-path status.

R02 §Resources and completions (adopt-guarded: every fact served here is also
reachable through a tool, so a client without resource support loses nothing).

Static resources (`colgrep://guide`, `colgrep://settings`, `colgrep://indexes`,
`colgrep://errors`) have no URI template variables, and the SDK's
`@mcp.resource` decorator refuses a `Context` parameter on a static resource —
there is nowhere for `ResourceManager.get_resource` to obtain a request
`Context` to inject (see `mcp.server.mcpserver.server.MCPServer.resource`).
They reach the one adapter the lifespan already built through
`server.get_app()`'s module-global handle instead (`get_adapter()`, no `ctx`).
Only the `colgrep://status/{+path}` template gets a request `Context` from
the SDK, so `status_resource` still takes `ctx` and threads it through, even
though `get_adapter` would resolve the very same adapter without it.

`guide()` and `errors_resource()` are pure functions of packaged/static data
(the guide file, `HINTS`); each delegates to a `functools.cache`d private
helper so the file read and the table render happen once per process instead
of once per request. The public functions stay plain `def`s rather than
carrying the cache decorator themselves: the SDK's `@mcp.resource` runs a
registered callable through `pydantic.validate_call`, which does not accept a
`functools._lru_cache_wrapper`.
"""

from __future__ import annotations

import functools
import importlib.resources
import re
import sys
from pathlib import Path
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context, ResourceSecurity
from mcp.server.mcpserver.exceptions import ResourceError

from .adapter import ColgrepError
from .errors import HINTS, Code, from_adapter_error
from .models import IndexList
from .server import get_adapter


def _map_adapter_error(exc: ColgrepError) -> ResourceError:
    """Wrap the same coded `[CODE] ... Next: ...` wording (`errors.from_adapter_error`)
    into `ResourceError`, the SDK's client-facing exception type for resources —
    a different class from the tool layer's `ToolError`."""
    return ResourceError(str(from_adapter_error(exc)))


#: A drive-rooted Windows path, e.g. `C:/Users/x` or `C:\Users\x`, optionally
#: with one redundant leading `/` (the same redundant slash the POSIX branch
#: below tolerates coming from `{+path}`).
_WIN_DRIVE_RE = re.compile(r"^/?([A-Za-z]:[/\\].*)$")


def _normalize_status_path(path: str) -> Path:
    """Accept `path` with or without a leading `/` and return an absolute `Path`.

    `{+path}` keeps inner slashes; the client may reasonably supply either
    `colgrep://status/Users/x/proj` or `colgrep://status//Users/x/proj`.

    On Windows a real absolute path is drive-rooted (`C:/Users/x`), never
    `/`-rooted — `pathlib` never considers a bare `/foo` "absolute" there
    without a drive. Unconditionally prepending `/` (the POSIX-only rule
    below) would turn an already-absolute Windows path into a non-absolute
    one, so a drive-rooted `path` is used as-is instead.
    """
    if sys.platform == "win32":
        m = _WIN_DRIVE_RE.match(path)
        if m:
            return Path(m.group(1))
    if not path.startswith("/"):
        path = "/" + path
    return Path(path)


@functools.cache
def _guide_text() -> str:
    return importlib.resources.files("colgrep_mcp").joinpath("guide.md").read_text()


def guide() -> str:
    """`colgrep://guide` — the packaged usage guide, verbatim."""
    return _guide_text()


async def settings_resource() -> dict[str, str]:
    """`colgrep://settings` — parsed `colgrep settings`."""
    adapter = get_adapter()
    try:
        return await adapter.settings()
    except ColgrepError as exc:
        raise _map_adapter_error(exc) from exc


async def indexes_resource() -> dict[str, Any]:
    """`colgrep://indexes` — every indexed project on this machine (`IndexList`)."""
    adapter = get_adapter()
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


@functools.cache
def _errors_text() -> str:
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


def errors_resource() -> str:
    """`colgrep://errors` — every coded failure/degradation and its hint, rendered from `HINTS`.

    An agent that only ever sees the `[CODE]` prefix (a `ToolError` message or
    a `SearchResult` note) can look the code up here for the full "next
    usage pattern" sentence without re-reading `guide.md` end to end.
    """
    return _errors_text()


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
