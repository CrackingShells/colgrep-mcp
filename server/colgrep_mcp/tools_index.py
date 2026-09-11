"""Read-only index inspection tools: `index_status`, `list_indexes`, `doctor`
(R01 §Tools). `index_build`/`index_clear` are added in this leaf's Step 2.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Annotated

from pydantic import Field

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolResult, TextContent, ToolAnnotations

from .adapter import ColgrepError, ColgrepFailed, ColgrepNotFound, ColgrepTimeout
from .models import Doctor, IndexInfo, IndexList, IndexStatus
from .paths import default_root, resolve_paths
from .server import get_adapter, get_settings


def _resolve_one(path: str | None, ctx: Context) -> Path:
    """Resolve a single optional path argument to one absolute, existing path."""
    settings = get_settings(ctx)
    return resolve_paths([path] if path else None, settings, None)[0]


def _translate_error(exc: ColgrepError) -> ToolError:
    """Map an adapter exception onto the `ToolError` text an agent should see (R01 §Error model)."""
    if isinstance(exc, ColgrepNotFound):
        return ToolError("colgrep not found on PATH. Install: cargo install colgrep — or set COLGREP_MCP_BINARY")
    if isinstance(exc, ColgrepFailed):
        tail = "\n".join(exc.stderr_tail.splitlines()[-20:])
        return ToolError(f"colgrep exited {exc.returncode} running {' '.join(exc.argv)}:\n{tail}")
    if isinstance(exc, ColgrepTimeout):
        return ToolError(f"{exc} — for a cold or large repository, call index_build first.")
    return ToolError(str(exc))


# --- rendering ---------------------------------------------------------------


def _render_status(status: IndexStatus) -> str:
    if not status.indexed:
        return f"Not indexed: {status.requested_path} (would create project {status.project})"
    lines = [f"Indexed: {status.project}", f"  model: {status.model or 'unknown'}"]
    if status.index_path:
        lines.append(f"  index: {status.index_path}")
    if status.units_indexed is not None:
        lines.append(f"  units_indexed: {status.units_indexed}")
    if status.search_count is not None:
        lines.append(f"  search_count: {status.search_count}")
    if status.requested_path != status.project:
        lines.append(f"  (requested {status.requested_path})")
    return "\n".join(lines)


def _render_index_list(result: IndexList) -> str:
    if not result.indexes:
        return "No indexed projects on this machine."
    return "\n".join(
        f"{i.project}  model={i.model}  units={i.units_indexed}  searches={i.search_count}" for i in result.indexes
    )


def _render_doctor(doc: Doctor) -> str:
    lines = [
        f"ok: {doc.ok}",
        f"colgrep_path: {doc.colgrep_path or 'NOT FOUND'}",
        f"version: {doc.version or 'unknown'}",
        f"default_root: {doc.default_root} (source: {doc.root_source})",
    ]
    if doc.settings:
        lines.append("settings: " + ", ".join(f"{k}={v}" for k, v in doc.settings.items()))
    for problem in doc.problems:
        lines.append(f"problem: {problem}")
    return "\n".join(lines)


# --- read-only tools ----------------------------------------------------------


async def index_status(
    path: Annotated[
        str | None,
        Field(description="Project directory to check; defaults to the resolved root (env/roots/cwd)."),
    ] = None,
    *,
    ctx: Context,
) -> CallToolResult:
    """Report whether a project is indexed by colgrep, and with what model/index."""
    adapter = get_adapter(ctx)
    resolved = _resolve_one(path, ctx)

    try:
        status = await adapter.status(resolved)
    except ColgrepError as exc:
        raise _translate_error(exc) from exc

    if status.indexed:
        try:
            stats = await adapter.stats()
        except ColgrepError:
            stats = []
        match = next(
            (info for info in stats if Path(info.project).resolve() == Path(status.project).resolve()),
            None,
        )
        if match is not None:
            status = status.model_copy(
                update={"units_indexed": match.units_indexed, "search_count": match.search_count}
            )

    return CallToolResult(
        content=[TextContent(type="text", text=_render_status(status))],
        structured_content=status.model_dump(),
    )


async def list_indexes(*, ctx: Context) -> CallToolResult:
    """List every project colgrep has indexed on this machine, with model and unit counts."""
    adapter = get_adapter(ctx)
    try:
        infos: list[IndexInfo] = await adapter.stats()
    except ColgrepError as exc:
        raise _translate_error(exc) from exc

    result = IndexList(indexes=infos)
    return CallToolResult(
        content=[TextContent(type="text", text=_render_index_list(result))],
        structured_content=result.model_dump(),
    )


async def doctor(*, ctx: Context) -> CallToolResult:
    """Check that colgrep is installed and reachable, and report the environment colgrep-mcp sees."""
    settings = get_settings(ctx)
    adapter = get_adapter(ctx)
    problems: list[str] = []

    colgrep_path = shutil.which(settings.binary)
    root, root_source = default_root(settings, roots=None)

    version: str | None = None
    try:
        version = await adapter.version()
    except ColgrepNotFound as exc:
        problems.append(f"colgrep binary not found: {exc}")
    except ColgrepError as exc:
        problems.append(f"colgrep --version failed: {exc}")

    settings_map: dict[str, str] = {}
    try:
        settings_map = await adapter.settings()
    except ColgrepError as exc:
        problems.append(f"colgrep settings failed: {exc}")

    doc = Doctor(
        colgrep_path=colgrep_path,
        version=version,
        settings=settings_map,
        default_root=str(root),
        root_source=root_source,
        ok=not problems,
        problems=problems,
    )
    return CallToolResult(
        content=[TextContent(type="text", text=_render_doctor(doc))],
        structured_content=doc.model_dump(),
    )


# --- registration --------------------------------------------------------------

_READ_ONLY = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False)


def register(mcp: MCPServer) -> None:
    """Attach this module's handlers to the server."""
    mcp.tool(title="Index status", annotations=_READ_ONLY)(index_status)
    mcp.tool(title="List indexes", annotations=_READ_ONLY)(list_indexes)
    mcp.tool(title="Doctor", annotations=_READ_ONLY)(doctor)
