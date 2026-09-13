"""Index management tools: `index_status`, `list_indexes`, `doctor`, `index_build`,
`index_clear` (R01 §Tools; R05 D2 heartbeat, D3 project-root refusal, M2 safe_log)
and `index_prune` (index_housekeeping R01 §C5).
"""

from __future__ import annotations

import asyncio
import contextlib
import shutil
import time
from pathlib import Path
from typing import Annotated, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.types import CallToolResult, ClientCapabilities, ElicitationCapability, TextContent, ToolAnnotations
from pydantic import BaseModel, Field

from . import store, tools_search
from .adapter import ColgrepAdapter, ColgrepError, ColgrepNotFound
from .errors import HINTS, Code, note, tool_error, translate_adapter_errors
from .locks import project_lock
from .logging_utils import safe_log, safe_notify_resource_updated, safe_progress
from .models import (
    Doctor,
    IndexBuildResult,
    IndexClearResult,
    IndexInfo,
    IndexList,
    IndexStatus,
    PruneCandidate,
    PruneResult,
)
from .paths import client_roots, default_root, resolve_target_paths
from .server import READ_ONLY_TOOL, get_adapter, get_settings, register_tool

#: Interval between indeterminate progress heartbeats during `index_build`
#: (R05 D2: colgrep emits no per-file progress, only a final summary line).
#: A module constant so tests can monkeypatch it down for fast heartbeat assertions.
HEARTBEAT_S = 5.0


class Confirm(BaseModel):
    """Elicitation schema for the human-in-the-loop confirmation of `index_clear` and `index_prune`."""

    confirm: bool


async def _resolve_one(path: str | None, ctx: Context) -> Path:
    """Resolve a single optional path argument to one absolute, existing path."""
    return (await resolve_target_paths(ctx, [path] if path else None))[0]


async def _confirmed(ctx: Context, confirm: bool, *, question: str, refusal: str) -> bool:
    """The one confirmation flow for a destructive tool (R05 M3; index_housekeeping R01 §C5).

    `confirm=true` short-circuits. Otherwise the client must advertise the
    elicitation capability, and the elicitation call itself must succeed —
    either failing is a technical refusal (`CONFIRMATION_REQUIRED`), never
    a silent decline (F8). Returns `False` only for a real decline.
    """
    if confirm:
        return True
    try:
        has_elicitation = ctx.session.check_client_capability(ClientCapabilities(elicitation=ElicitationCapability()))
    except Exception:  # noqa: BLE001 - treat any capability-check failure as "unavailable"
        has_elicitation = False
    if not has_elicitation:
        raise tool_error(Code.CONFIRMATION_REQUIRED, refusal)
    try:
        res = await ctx.elicit(question, schema=Confirm)
    except Exception as exc:  # noqa: BLE001 - the elicitation call itself failing
        # (e.g. `NoBackChannelError`) is a technical failure, not a user
        # decision — it must not be collapsed into the same silent
        # "declined" response a real decline gets.
        raise tool_error(Code.CONFIRMATION_REQUIRED, f"{refusal[:-1]} (elicitation failed: {exc}).") from exc
    return res.action == "accept" and bool(res.data.confirm)


def _match_stats(status: IndexStatus, stats: list[IndexInfo]) -> IndexInfo | None:
    """Find `status.project`'s entry in `stats` without a `Path.resolve()` syscall per candidate.

    `status.project` and `info.project` are usually the same string colgrep
    reported for the same project, so a plain string comparison matches the
    common case with no filesystem access at all. Only when nothing matches
    that way do we pay for resolving each `info.project` (symlinks, a
    trailing `/.`, ...) against the one already-resolved `status.project`.
    """
    match = next((info for info in stats if info.project == status.project), None)
    if match is not None:
        return match
    target = Path(status.project).resolve()
    return next((info for info in stats if Path(info.project).resolve() == target), None)


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


def _mib(size_bytes: int) -> str:
    return f"{size_bytes / 2**20:.1f}MiB"


def _human_size(size_bytes: int) -> str:
    return f"{size_bytes / 2**30:.2f}GiB" if size_bytes >= 2**30 else _mib(size_bytes)


def _index_block(info: IndexInfo) -> str:
    """The pre-0.5 four tokens first, then the store-derived ones (index_housekeeping
    R01 §C4): a client that read the old line still finds it at the front."""
    text = f"{info.project}  model={info.model}  units={info.units_indexed}  searches={info.search_count}"
    if info.size_bytes is not None:
        text += f"  size={_mib(info.size_bytes)}"
    if info.last_modified:
        text += f"  modified={info.last_modified[:10]}"
    if info.stale == store.SHADOWED:
        text += f"  [shadowed by {info.shadowed_by}]"
    elif info.stale:
        text += f"  [{info.stale}]"
    return text


def _index_header(result: IndexList, stale_only: bool) -> str:
    shown = len(result.indexes)
    total = result.total if result.total is not None else shown
    header = (
        f"{shown} stale of {total} indexed projects on this machine"
        if stale_only
        else f"{shown} indexed projects on this machine"
    )
    if result.total_bytes is None:
        return header
    counts = {kind: sum(1 for i in result.indexes if i.stale == kind) for kind in store.STALE_CLASSES}
    return (
        f"{header} ({_human_size(result.total_bytes)} in store; {counts[store.ORPHANED]} orphaned, "
        f"{counts[store.MACHINE_STATE]} machine-state, {counts[store.SHADOWED]} shadowed)"
    )


def _render_index_list(result: IndexList, budget: int, *, stale_only: bool = False) -> tuple[str, bool]:
    """Render `result` through the one budgeted renderer (R01 §C7), capped at
    `budget` chars like every other tool's text listing (R01 consistency
    §Token-budget invariant); `list_indexes`' text is machine-global and was
    observed at 24 kB unbounded on one machine (`KT-B`).

    The empty-list sentence is a fixed string, not a zero-block render
    through `_render_budgeted` (which would need a header even with nothing
    to list) — kept byte-identical to the pre-budget rendering.
    """
    if not result.indexes:
        if stale_only and result.total:
            return f"No stale indexes among the {result.total} indexed projects on this machine.", False
        return "No indexed projects on this machine.", False
    header = _index_header(result, stale_only)
    blocks = [_index_block(info) for info in result.indexes]
    return tools_search._render_budgeted(
        header, blocks, lambda remaining: f"[{remaining} more indexes in structured_content]", [], budget
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
    for hint in doc.hints:
        lines.append(f"hint: {hint}")
    return "\n".join(lines)


def _candidate_block(c: PruneCandidate) -> str:
    text = f"  {c.project}  size={_mib(c.size_bytes)}  modified={c.last_modified[:10]}  searches={c.search_count}"
    if c.shadowed_by:
        text += f"  shadowed by {c.shadowed_by}"
    return text


def _render_prune(result: PruneResult, classes: list[str], budget: int) -> tuple[str, bool]:
    """Candidates grouped by class through the one budgeted renderer (R01 §C7), the exact
    next call as the trailing note (index_housekeeping R01 §C5)."""
    if not result.candidates:
        return f"Nothing to prune in {result.store_root} for classes {classes}.", False
    n = len(result.candidates)
    if result.dry_run:
        header = f"{n} prune candidates ({_human_size(result.total_bytes)}) in {result.store_root}"
        classes_arg = "[" + ", ".join(f'"{c}"' for c in classes) + "]"
        notes = [
            "Dry run: nothing removed. Call "
            f"index_prune(dry_run=false, confirm=true, classes={classes_arg}) to remove them."
        ]
    else:
        header = (
            f"Pruned {len(result.pruned)} of {n} indexes ({_human_size(result.freed_bytes)} freed) "
            f"from {result.store_root}"
        )
        notes = [f"failed: {line}" for line in result.failed]
    blocks: list[str] = []
    for kind in store.PRUNE_CLASSES:
        group = [c for c in result.candidates if c.kind == kind]
        if not group:
            continue
        blocks.append(f"{kind} ({len(group)}, {_human_size(sum(c.size_bytes for c in group))}):")
        blocks += [_candidate_block(c) for c in group]
    return tools_search._render_budgeted(
        header, blocks, lambda remaining: f"  [{remaining} more lines in structured_content]", notes, budget
    )


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
        match = _match_stats(status, stats)
        if match is not None:
            status = status.model_copy(
                update={"units_indexed": match.units_indexed, "search_count": match.search_count}
            )

    return CallToolResult(
        content=[TextContent(type="text", text=_render_status(status))],
        structured_content=status.model_dump(),
    )


async def list_indexes(
    stale_only: Annotated[
        bool,
        Field(
            description="Only indexes whose project path is gone (`orphaned`), sits in a temp, cache or hidden "
            "tree (`machine_state`), or lies inside another indexed project (`shadowed`)."
        ),
    ] = False,
    *,
    ctx: Context,
) -> CallToolResult:
    """List every project colgrep has indexed on this machine: model, units, searches, index size,
    last use, whether the path still exists and whether another indexed project shadows it.
    Use `index_prune` to remove the stale ones."""
    adapter = get_adapter(ctx)
    settings = get_settings(ctx)
    async with translate_adapter_errors():
        result = await store.index_list(adapter, stale_only=stale_only)

    text, capped = _render_index_list(result, settings.text_budget, stale_only=stale_only)
    if capped:
        await safe_log(
            ctx,
            "warning",
            f"list_indexes text truncated to {settings.text_budget} chars; see structured_content for all indexes",
        )

    return CallToolResult(
        content=[TextContent(type="text", text=text)],
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

    hints: list[str] = []
    if version is not None:
        hints = await _store_hints(adapter)

    doc = Doctor(
        colgrep_path=colgrep_path,
        version=version,
        settings=settings_map,
        default_root=str(root),
        root_source=root_source,
        ok=not problems,
        problems=problems,
        hints=hints,
    )
    return CallToolResult(
        content=[TextContent(type="text", text=_render_doctor(doc))],
        structured_content=doc.model_dump(),
    )


async def _store_hints(adapter: ColgrepAdapter) -> list[str]:
    """`doctor`'s look at the index store (index_housekeeping R01 §C6, D9): a hint, never a
    problem, when the store carries orphaned or machine-state indexes — or when every
    indexed project is gone, so the store cannot even be located. A fresh machine with
    no index at all gets no hint; a `--stats` failure is left to the tools that need it.
    """
    try:
        infos = await adapter.stats()
        root = await adapter.store_root(infos)
    except ColgrepError:
        return []
    if root is None:
        if infos:
            return [note(Code.INDEX_STORE_UNKNOWN, f"{len(infos)} indexed projects, none of which exists on disk.")]
        return []
    entries = await asyncio.to_thread(store.read_store, root)
    verdicts = store.classify_now(entries)
    orphaned = [v for v in verdicts if v.kind == store.ORPHANED]
    machine = [v for v in verdicts if v.kind == store.MACHINE_STATE]
    if not orphaned and not machine:
        return []
    size = sum(v.entry.size_bytes for v in (*orphaned, *machine))
    return [
        note(
            Code.INDEX_STORE_STALE,
            f"{len(orphaned)} orphaned and {len(machine)} machine-state indexes ({_human_size(size)}) in {root}. "
            f"{HINTS[Code.INDEX_STORE_STALE]}",
        )
    ]


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
                    await safe_progress(ctx, elapsed_s, None, f"indexing {resolved} … {int(elapsed_s)}s")

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

    ok = await _confirmed(
        ctx,
        confirm,
        question=f"Delete the colgrep index for {resolved}? This cannot be undone.",
        refusal=f"Refusing to delete the index for {resolved} without confirmation.",
    )
    if not ok:
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


PruneClass = Literal["orphaned", "machine_state", "shadowed", "cold"]


async def index_prune(
    classes: Annotated[
        list[PruneClass],
        Field(
            description="Which indexes count as candidates: `orphaned` (project path gone), `machine_state` "
            "(temp, cache or hidden tree), `shadowed` (inside another indexed project), `cold` (at most "
            "`max_searches` searches and untouched for `days`; opt-in)."
        ),
    ] = ["orphaned", "machine_state", "shadowed"],  # noqa: B006 - pydantic copies the default per call
    days: Annotated[int, Field(description="Age in days for `cold`.", ge=0)] = 30,
    max_searches: Annotated[int, Field(description="Search count at or below which an index is `cold`.", ge=0)] = 1,
    dry_run: Annotated[bool, Field(description="List the candidates without removing anything (default).")] = True,
    confirm: Annotated[bool, Field(description="With dry_run=false: remove without an elicitation prompt.")] = False,
    *,
    ctx: Context,
) -> CallToolResult:
    """Remove stale colgrep indexes in one call instead of one `index_clear` per project: orphaned
    (path gone), machine-state (temp, cache, hidden tree), shadowed (inside another indexed project)
    and, opt-in, cold ones. Dry run by default; `dry_run=false` with `confirm=true` or an accepted
    elicitation deletes the index directories. Never touches a live project's index."""
    adapter = get_adapter(ctx)
    settings = get_settings(ctx)

    async with translate_adapter_errors():
        infos = await adapter.stats()
        root = await adapter.store_root(infos)
    if root is None:
        raise tool_error(Code.INDEX_STORE_UNKNOWN, "No indexed project exists on disk, so the store cannot be located.")

    entries = await asyncio.to_thread(store.read_store, root)
    verdicts = store.classify_now(entries, days=days, max_searches=max_searches)
    candidates = [
        PruneCandidate(
            project=v.entry.project,
            index_dir=str(v.entry.index_dir),
            kind=v.kind,
            size_bytes=v.entry.size_bytes,
            last_modified=store.iso_utc(v.entry.last_modified),
            search_count=v.entry.search_count,
            shadowed_by=v.shadowed_by,
        )
        for v in verdicts
        if v.kind is not None and v.kind in classes
    ]
    result = PruneResult(
        dry_run=dry_run,
        store_root=str(root),
        candidates=candidates,
        total_bytes=sum(c.size_bytes for c in candidates),
    )

    if not dry_run and candidates:
        ok = await _confirmed(
            ctx,
            confirm,
            question=(
                f"Remove {len(candidates)} colgrep indexes ({_human_size(result.total_bytes)}) from {root}? "
                "This cannot be undone."
            ),
            refusal=f"Refusing to remove {len(candidates)} indexes from {root} without confirmation.",
        )
        if not ok:
            return CallToolResult(
                content=[TextContent(type="text", text="Not pruned (declined)")],
                structured_content=result.model_copy(update={"dry_run": True}).model_dump(),
            )
        for c in candidates:
            async with project_lock(Path(c.project)):
                try:
                    # Not through `translate_adapter_errors`: one refused or failed
                    # removal must not abort the batch, it lands in `failed`.
                    await asyncio.to_thread(store.remove_index_dir, root, Path(c.index_dir), c.project)
                except (store.StoreError, OSError) as exc:
                    result.failed.append(f"{c.project}: {exc}")
                    continue
            result.pruned.append(c.project)
            result.freed_bytes += c.size_bytes
        if result.pruned:
            await safe_notify_resource_updated(ctx, "colgrep://indexes")

    text, capped = _render_prune(result, list(classes), settings.text_budget)
    if capped:
        budget = settings.text_budget
        await safe_log(ctx, "warning", f"index_prune text truncated to {budget} chars; see structured_content")
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        structured_content=result.model_dump(),
    )


# --- registration --------------------------------------------------------------


def register(mcp: MCPServer) -> None:
    """Attach this module's handlers to the server."""
    register_tool(mcp, index_status, title="Index status", annotations=READ_ONLY_TOOL)
    register_tool(mcp, list_indexes, title="List indexes", annotations=READ_ONLY_TOOL)
    register_tool(mcp, doctor, title="Doctor", annotations=READ_ONLY_TOOL)
    register_tool(
        mcp,
        index_build,
        title="Build or refresh index",
        annotations=ToolAnnotations(
            read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False
        ),
    )
    register_tool(
        mcp,
        index_clear,
        title="Clear index",
        annotations=ToolAnnotations(destructive_hint=True, open_world_hint=False),
    )
    register_tool(
        mcp,
        index_prune,
        title="Prune stale indexes",
        annotations=ToolAnnotations(destructive_hint=True, idempotent_hint=True, open_world_hint=False),
    )
