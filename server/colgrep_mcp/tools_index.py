"""Index management tools: `index_status`, `list_indexes`, `doctor`, `index_build`,
`index_clear` (R01 §Tools; R05 D2 heartbeat, D3 project-root refusal, M2 safe_log).
"""

from __future__ import annotations

import asyncio
import contextlib
import shutil
import time
from pathlib import Path
from typing import Annotated

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.types import CallToolResult, ClientCapabilities, ElicitationCapability, TextContent, ToolAnnotations
from pydantic import BaseModel, Field

from .adapter import ColgrepError, ColgrepNotFound
from .errors import Code, tool_error, translate_adapter_errors
from .locks import project_lock
from .logging_utils import safe_log, safe_notify_resource_updated, safe_progress
from .models import Doctor, IndexBuildResult, IndexClearResult, IndexInfo, IndexList, IndexStatus
from .paths import client_roots, default_root, resolve_target_paths
from .server import READ_ONLY_TOOL, get_adapter, get_settings

#: Interval between indeterminate progress heartbeats during `index_build`
#: (R05 D2: colgrep emits no per-file progress, only a final summary line).
#: A module constant so tests can monkeypatch it down for fast heartbeat assertions.
HEARTBEAT_S = 5.0


class Confirm(BaseModel):
    """Elicitation schema for `index_clear`'s human-in-the-loop confirmation."""

    confirm: bool


async def _resolve_one(path: str | None, ctx: Context) -> Path:
    """Resolve a single optional path argument to one absolute, existing path."""
    return (await resolve_target_paths(ctx, [path] if path else None))[0]


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


def _build_summary_line(result: IndexBuildResult) -> str:
    if result.up_to_date:
        return f"Index is up to date for {result.project}"
    return (
        f"Indexed {result.project} "
        f"(added: {result.added}, changed: {result.changed}, deleted: {result.deleted}, "
        f"unchanged: {result.unchanged})"
    )


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
    resolved = await _resolve_one(path, ctx)

    async with translate_adapter_errors(path=resolved):
        status = await adapter.status(resolved)

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
    async with translate_adapter_errors():
        infos: list[IndexInfo] = await adapter.stats()

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
    roots = await client_roots(ctx) if settings.root is None else None
    root, root_source = default_root(settings, roots)

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


# --- mutating tools ------------------------------------------------------------


async def index_build(
    path: Annotated[
        str | None,
        Field(description="Project directory to (re)index; defaults to the resolved root."),
    ] = None,
    force_cpu: Annotated[bool, Field(description="Force CPU execution instead of GPU for this build.")] = False,
    *,
    ctx: Context,
) -> CallToolResult:
    """Build or refresh the colgrep index for a project, streaming heartbeat progress while it runs."""
    adapter = get_adapter(ctx)
    resolved = await _resolve_one(path, ctx)

    async def _forward_stderr(line: str) -> None:
        await safe_log(ctx, "info", line)

    streaming_adapter = adapter.with_stderr(_forward_stderr)

    start = time.monotonic()
    async with project_lock(resolved):
        task: asyncio.Task[IndexBuildResult] = asyncio.ensure_future(
            streaming_adapter.init(resolved, force_cpu=force_cpu)
        )
        try:
            async with translate_adapter_errors(path=resolved):
                while True:
                    done, _pending = await asyncio.wait({task}, timeout=HEARTBEAT_S)
                    if task in done:
                        break
                    elapsed_s = time.monotonic() - start
                    await safe_progress(
                        ctx, elapsed_s, None, f"indexing {resolved} … {int(elapsed_s)}s"
                    )

                result = await task
        finally:
            # `asyncio.wait` (unlike `gather`) never propagates cancellation
            # to the task it's waiting on: if *this* coroutine is cancelled
            # while inside the loop above, `task` (and its colgrep
            # subprocess) would otherwise be silently dropped, still
            # running — and the `async with project_lock` below would
            # release the lock regardless, defeating "held for the whole
            # build" for exactly the case that matters most. Cancel and
            # await it here, before the lock's `__aexit__` runs.
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    summary_line = _build_summary_line(result)
    await safe_progress(ctx, 1, 1, summary_line)
    await safe_notify_resource_updated(ctx, "colgrep://indexes")

    return CallToolResult(
        content=[TextContent(type="text", text=summary_line)],
        structured_content=result.model_dump(),
    )


async def index_clear(
    path: Annotated[
        str | None,
        Field(description="Project directory whose index to delete; defaults to the resolved root."),
    ] = None,
    confirm: Annotated[
        bool,
        Field(description="Must be true to delete without an interactive confirmation prompt."),
    ] = False,
    *,
    ctx: Context,
) -> CallToolResult:
    """Delete a project's colgrep index. Destructive: asks for confirmation unless confirm=true."""
    adapter = get_adapter(ctx)
    resolved = await _resolve_one(path, ctx)

    async with translate_adapter_errors(path=resolved):
        st = await adapter.status(resolved)

    if st.indexed and Path(st.project).resolve() != resolved.resolve():
        raise tool_error(
            Code.PROJECT_ROOT_MISMATCH,
            f"colgrep would clear the index for {st.project}, which also covers other directories than {resolved}.",
        )

    if not confirm:
        has_elicitation = False
        try:
            has_elicitation = ctx.session.check_client_capability(
                ClientCapabilities(elicitation=ElicitationCapability())
            )
        except Exception:  # noqa: BLE001 - treat any capability-check failure as "unavailable"
            has_elicitation = False

        if not has_elicitation:
            raise tool_error(
                Code.CONFIRMATION_REQUIRED,
                f"Refusing to delete the index for {resolved} without confirmation.",
            )

        try:
            res = await ctx.elicit(
                f"Delete the colgrep index for {resolved}? This cannot be undone.",
                schema=Confirm,
            )
        except Exception as exc:  # noqa: BLE001 - the elicitation call itself failing
            # (e.g. `NoBackChannelError`) is a technical failure, not a user
            # decision — it must not be collapsed into the same silent
            # `cleared=False` "declined" response a real decline gets.
            # Surface the same coded refusal as "no elicitation capability".
            raise tool_error(
                Code.CONFIRMATION_REQUIRED,
                f"Refusing to delete the index for {resolved} without confirmation "
                f"(elicitation failed: {exc}).",
            ) from exc

        if res.action != "accept" or not res.data.confirm:
            result = IndexClearResult(project=str(resolved), cleared=False)
            return CallToolResult(
                content=[TextContent(type="text", text="Not cleared (declined)")],
                structured_content=result.model_dump(),
            )

    async with project_lock(resolved):
        async with translate_adapter_errors(path=resolved):
            await adapter.clear(resolved)

    result = IndexClearResult(project=str(resolved), cleared=True)
    await safe_notify_resource_updated(ctx, "colgrep://indexes")

    return CallToolResult(
        content=[TextContent(type="text", text=f"Cleared index for {resolved}")],
        structured_content=result.model_dump(),
    )


# --- registration --------------------------------------------------------------


def register(mcp: MCPServer) -> None:
    """Attach this module's handlers to the server."""
    mcp.tool(title="Index status", annotations=READ_ONLY_TOOL)(index_status)
    mcp.tool(title="List indexes", annotations=READ_ONLY_TOOL)(list_indexes)
    mcp.tool(title="Doctor", annotations=READ_ONLY_TOOL)(doctor)
    mcp.tool(
        title="Build or refresh index",
        annotations=ToolAnnotations(
            read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False
        ),
    )(index_build)
    mcp.tool(
        title="Clear index",
        annotations=ToolAnnotations(destructive_hint=True, open_world_hint=False),
    )(index_clear)
