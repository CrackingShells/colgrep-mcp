"""Tool module `tools_search`: `search`, `find_files`, `expand` (R01 §Tools).

Step 1 provides the pure helpers the three tool handlers compose: converting
a raw colgrep hit into a `SearchHit` (re-locating its true source lines per
R05 D1), and rendering `SearchResult`/`FileResult` into the compact,
token-budgeted text shown to the model (R01 §Token-budget invariant). Step 2
registers the three tools themselves on top of those helpers.
"""

from __future__ import annotations

import asyncio
import re
import time
import warnings
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Annotated

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import Field

from .adapter import (
    ColgrepFailed,
    ColgrepNotFound,
    ColgrepParseError,
    ColgrepTimeout,
    RawHit,
    SearchRequest,
)
from .errors import Code, from_adapter_error, note, tool_error
from .locate import locate_unit
from .locks import project_lock
from .logging_utils import safe_log
from .models import ExpandedUnit, ExpandResult, FileHit, FileResult, SearchHit, SearchResult
from .paths import resolve_paths
from .server import get_adapter, get_settings

#: Strict `hit_id` shape (R01 §hit_id invariant): "<absolute file>:<line>-<end_line>".
_HIT_ID_RE = re.compile(r"^(.+):(\d+)-(\d+)$")


def _resolve_hit_file(file: str, base_path: Path | None) -> str:
    """Make a hit's `unit.file` absolute before it's used anywhere else (R01
    §hit_id invariant).

    colgrep is expected to always emit an absolute path (R05), but nothing
    stops a future/odd colgrep build from emitting a relative one. A relative
    `file` left as-is would build a `hit_id` that `expand` later resolves
    against the *server process's* cwd rather than the project actually
    searched — silently reading (or failing to read) the wrong file. Joining
    against `base_path` (the first path this search itself ran against) is
    the only meaningful "relative to what" available here; an already-
    absolute `file`, or a missing `base_path`, passes through unchanged (no
    forced `.resolve()` — that would canonicalise symlinks, out of scope
    here per F7).
    """
    if not file or base_path is None or Path(file).is_absolute():
        return file
    return str(base_path / file)


def hit_from_raw(
    raw: RawHit,
    snippet_lines: int,
    include_code: bool,
    file_cache: dict[str, str],
    base_path: Path | None = None,
) -> SearchHit:
    """Build a `SearchHit` from one raw colgrep JSON hit (`{"unit": {...}, "score": ...}`).

    Re-derives `line`/`end_line` via `locate_unit` (R05 D1: colgrep's reported
    values are frequently wrong) so `hit_id` is built from trustworthy
    locations. Pure and I/O-free: `file_cache` must already hold every hit
    file's text (or `""` for an unreadable one) — the async caller fills it
    via `_fill_file_cache` (off the event loop, R05 F11) before this runs, so
    an unreadable file still degrades to an empty text rather than raise,
    which makes `locate_unit` fall back to the reported line/end_line with
    `verified=False`. `base_path` (the first path the search ran against)
    resolves a relative `unit.file` to absolute (F13) before `hit_id` is built.

    Tolerant of missing/None optional fields (R03 §Hit JSON Schema): only
    `unit`/`score` are assumed present, everything else defaults to an empty
    string or `None`.
    """
    unit = raw.get("unit") or {}
    score = float(raw.get("score") or 0.0)
    file = _resolve_hit_file(unit.get("file") or "", base_path)
    code = unit.get("code") or ""
    reported_line = int(unit.get("line") or 1)
    reported_end = int(unit.get("end_line") or reported_line)

    file_text = file_cache.get(file, "")

    line, end_line, verified = locate_unit(file_text, code, reported_line, reported_end)
    hit_id = f"{file}:{line}-{end_line}"

    code_lines = code.splitlines()
    snippet = "\n".join(code_lines[:snippet_lines]) if code_lines else None

    return SearchHit(
        hit_id=hit_id,
        file=file,
        line=line,
        end_line=end_line,
        name=unit.get("name") or "",
        qualified_name=unit.get("qualified_name") or "",
        unit_type=unit.get("unit_type") or "",
        language=unit.get("language") or "",
        signature=unit.get("signature"),
        score=score,
        snippet=snippet,
        code=code if include_code and code else None,
        location_verified=verified,
    )


async def _read_file_off_loop(file: str) -> str:
    """`Path(file).read_text(errors="replace")`, run in a worker thread.

    A hit's file can be arbitrarily large; reading it directly on the event
    loop would block every other in-flight request for as long as the read
    takes (F11). An unreadable file degrades to `""` (the same fallback
    `hit_from_raw` used to produce on `OSError`), not an exception.
    """
    try:
        return await asyncio.to_thread(Path(file).read_text, errors="replace")
    except OSError:
        return ""


async def _fill_file_cache(
    raw_hits: list[RawHit], file_cache: dict[str, str], base_path: Path | None = None
) -> None:
    """Read every distinct hit file referenced by `raw_hits` into `file_cache`,
    at most once per file, concurrently and off the event loop (F11).

    Keyed the same way `hit_from_raw` looks values up: `base_path` resolves a
    relative `unit.file` to absolute first (F13), so a relative and an
    equivalent already-absolute reference to the same file share one cache
    entry and one read.
    """
    files = {_resolve_hit_file((raw.get("unit") or {}).get("file") or "", base_path) for raw in raw_hits}
    missing = [f for f in files if f not in file_cache]
    if not missing:
        return
    texts = await asyncio.gather(*(_read_file_off_loop(f) for f in missing))
    file_cache.update(zip(missing, texts, strict=True))


def _search_header(result: SearchResult) -> str:
    parts = [f'{result.total} hits for "{result.query}"']
    if result.pattern:
        parts.append(f"pattern={result.pattern!r}")
    parts.append(f"in {', '.join(result.paths)}")
    return " ".join(parts) + f" — {result.elapsed_ms}ms"


def _hit_block(hit: SearchHit) -> str:
    head = f"{hit.file}:{hit.line}-{hit.end_line}  score={hit.score:.2f}  {hit.unit_type} {hit.name} — {hit.signature or ''}"
    if not hit.snippet:
        return head
    indented = "\n".join(f"  {line}" for line in hit.snippet.splitlines())
    return f"{head}\n{indented}"


def render_search_text(result: SearchResult, budget: int) -> tuple[str, bool]:
    """Render `result` as the compact text shown to the model, capped at `budget` chars.

    Header line, then one block per hit (`file:line-end  score  unit_type
    name — signature`, snippet indented two spaces), stopping before any hit
    whose block would push the text past `budget`. When hits were dropped, a
    `[K more hits ...]` continuation note is appended — and the cap is a hard
    one (R01 §Token-budget invariant: "capped at N characters"), so if the
    note itself would overflow `budget` a previously-emitted hit is dropped
    to make room for it, repeatedly if needed, rather than let the note push
    the text past the limit. Trailing `result.notes` (e.g. R05 D5's
    exhaustive-search caveat) are always appended last, so a zero-hit result
    still renders them — but the cap stays hard even then: if `budget` is
    too small to fit even the header (plus the mandatory note, plus
    `result.notes`) with nothing left to drop, the joined text is
    hard-truncated to `budget` characters as the last resort, rather than
    ever returning more than requested.

    Returns `(text, was_capped)`; `was_capped` reflects only this rendering
    step, not `result.truncated` (which may already be true upstream).
    """
    header = _search_header(result)
    blocks = [header]
    text_len = len(header)
    capped = False
    emitted = 0

    for hit in result.hits:
        block = _hit_block(hit)
        candidate_len = text_len + 1 + len(block)
        if candidate_len > budget:
            capped = True
            break
        blocks.append(block)
        text_len = candidate_len
        emitted += 1

    remaining = len(result.hits) - emitted
    if capped and remaining > 0:
        # Bounded by construction: each non-appending iteration drops one
        # previously-emitted hit, so this runs at most `emitted + 1` times
        # (one drop per already-emitted hit, plus the final appending pass)
        # before either fitting or running out of hits to drop.
        for _ in range(emitted + 1):
            note = f"[{remaining} more hits in structured_content; call expand(hit_ids=[...]) for code]"
            candidate_len = text_len + 1 + len(note)
            if candidate_len <= budget or emitted == 0:
                blocks.append(note)
                text_len = candidate_len
                break
            dropped = blocks.pop()
            text_len -= len(dropped) + 1
            emitted -= 1
            remaining += 1

    text = "\n".join(blocks)
    for note in result.notes:
        text = f"{text}\n{note}"

    # Hard cap (R01 §Token-budget invariant): the backtracking above can
    # still leave `header (+ note) (+ result.notes)` longer than `budget`
    # when `budget` is smaller than that unavoidable minimum — hard-truncate
    # as the last resort rather than ever exceed what was requested.
    if len(text) > budget:
        text = text[:budget]
        capped = True

    return text, capped


def _files_header(result: FileResult) -> str:
    parts = [f'{len(result.files)} files for "{result.query}"']
    if result.pattern:
        parts.append(f"pattern={result.pattern!r}")
    parts.append(f"in {', '.join(result.paths)}")
    return " ".join(parts) + f" — {result.elapsed_ms}ms"


def _file_block(file_hit: FileHit) -> str:
    units = ", ".join(file_hit.top_units)
    return f"{file_hit.file}  score={file_hit.best_score:.2f}  {file_hit.hits} hits — {units}"


def render_files_text(result: FileResult, budget: int) -> tuple[str, bool]:
    """`find_files` counterpart of `render_search_text`: one line per file, same hard-budget rule."""
    header = _files_header(result)
    blocks = [header]
    text_len = len(header)
    capped = False
    emitted = 0

    for file_hit in result.files:
        block = _file_block(file_hit)
        candidate_len = text_len + 1 + len(block)
        if candidate_len > budget:
            capped = True
            break
        blocks.append(block)
        text_len = candidate_len
        emitted += 1

    remaining = len(result.files) - emitted
    if capped and remaining > 0:
        # Bounded by construction: same reasoning as `render_search_text`.
        for _ in range(emitted + 1):
            note = f"[{remaining} more files in structured_content]"
            candidate_len = text_len + 1 + len(note)
            if candidate_len <= budget or emitted == 0:
                blocks.append(note)
                text_len = candidate_len
                break
            dropped = blocks.pop()
            text_len -= len(dropped) + 1
            emitted -= 1
            remaining += 1

    text = "\n".join(blocks)

    # Hard cap — see `render_search_text`'s matching comment.
    if len(text) > budget:
        text = text[:budget]
        capped = True

    return text, capped


async def _client_roots(ctx: Context) -> list[Path] | None:
    """Best-effort client `roots` (R01 §Path resolution invariant, R05 M1).

    `roots/list` is deprecated as of the 2026-07-28 protocol revision and may
    raise `NoBackChannelError` (or just a deprecation warning) on a client
    with no back-channel; either way this degrades to `None` rather than
    fail the tool call, leaving `resolve_paths` to fall through to cwd.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = await ctx.session.list_roots()
    except Exception:
        return None
    if not result.roots:
        return None
    try:
        return [Path(root.uri.path) for root in result.roots if root.uri.path]
    except Exception:
        return None


async def _do_search(
    ctx: Context,
    *,
    query: str,
    paths: list[str] | None,
    pattern: str | None,
    fixed_string: bool,
    whole_word: bool,
    case_sensitive: bool,
    include: list[str] | None,
    exclude: list[str] | None,
    exclude_dir: list[str] | None,
    limit: int | None,
    code_only: bool,
    semantic_only: bool,
    alpha: float | None,
    skip_index_update: bool,
    snippet_lines: int,
    include_code: bool,
) -> tuple[SearchResult, list[SearchHit]]:
    """Shared body of `search` and `find_files`: resolve, lock, run, convert.

    Raises `ToolError` (via `resolve_paths` for a bad path, via
    `_translate_error` for an adapter failure); never a bare adapter
    exception.
    """
    settings = get_settings(ctx)
    roots = await _client_roots(ctx)
    resolved = resolve_paths(paths, settings, roots)

    stderr_lines: list[str] = []

    async def on_stderr(line: str) -> None:
        stderr_lines.append(line)
        await safe_log(ctx, "info", line)

    adapter = get_adapter(ctx).with_stderr(on_stderr)
    req = SearchRequest(
        query=query,
        paths=resolved,
        pattern=pattern,
        fixed_string=fixed_string,
        whole_word=whole_word,
        case_sensitive=case_sensitive,
        include=include or [],
        exclude=exclude or [],
        exclude_dir=exclude_dir or [],
        limit=limit,
        code_only=code_only,
        semantic_only=semantic_only,
        alpha=alpha,
        skip_index_update=skip_index_update,
    )

    start = time.monotonic()
    # Lock every distinct project a multi-path search touches (R01
    # §Concurrency invariant: "held [for] search/find_files too"), not only
    # `resolved[0]` — otherwise a concurrent `index_build`/search on the
    # second-and-later paths races this call. Sorted so two overlapping
    # multi-path calls always acquire their shared locks in the same order,
    # avoiding a lock-ordering deadlock.
    distinct_paths = sorted(set(resolved), key=str)
    async with AsyncExitStack() as stack:
        for p in distinct_paths:
            await stack.enter_async_context(project_lock(p))
        try:
            raw_hits = await adapter.search(req)
        except (ColgrepNotFound, ColgrepFailed, ColgrepTimeout, ColgrepParseError) as exc:
            raise from_adapter_error(exc, path=resolved[0]) from exc
    elapsed_ms = int((time.monotonic() - start) * 1000)

    # F13: `resolved[0]` is the "first search path" a relative `unit.file`
    # (not expected from colgrep, but not guaranteed absent either) resolves
    # against.
    base_path = resolved[0]
    file_cache: dict[str, str] = {}
    await _fill_file_cache(raw_hits, file_cache, base_path=base_path)
    hits = [hit_from_raw(raw, snippet_lines, include_code, file_cache, base_path=base_path) for raw in raw_hits]

    notes: list[str] = []
    if not hits:
        notes.append(note(Code.NO_HITS, "no units matched"))
    if limit is None and pattern is None:
        # R05 D5: colgrep only searches exhaustively (omits its own default cap)
        # when a `-e` pattern is present; a bare semantic query still gets 15 hits.
        notes.append(
            note(Code.LIMIT_DEFAULT_APPLIED, "limit omitted without pattern: colgrep applies its own default of 15")
        )
    if any(not hit.location_verified for hit in hits):
        # R05 D1: once per result, never once per hit, so a result with many
        # unverified hits doesn't drown other notes.
        notes.append(note(Code.LOCATION_UNVERIFIED, "some hits' line numbers are unverified"))

    result = SearchResult(
        query=query,
        pattern=pattern,
        paths=[str(p) for p in resolved],
        hits=hits,
        total=len(hits),
        truncated=False,
        elapsed_ms=elapsed_ms,
        index_updated=any("Building index" in line for line in stderr_lines),  # R05 D7
        notes=notes,
    )
    return result, hits


def register(mcp: MCPServer) -> None:
    """Attach `search`, `find_files` and `expand` to the server."""

    @mcp.tool(
        title="Search code",
        annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False),
    )
    async def search(
        ctx: Context,
        query: Annotated[str, Field(description="Natural-language description of the behaviour you are looking for.")],
        paths: Annotated[
            list[str] | None, Field(description="Files/directories to search (default: the project root).")
        ] = None,
        pattern: Annotated[
            str | None,
            Field(description="Regex pre-filter (hybrid mode): only units whose text matches are ranked."),
        ] = None,
        fixed_string: Annotated[bool, Field(description="Treat `pattern` as a literal string, not a regex.")] = False,
        whole_word: Annotated[bool, Field(description="Match `pattern` on whole words only.")] = False,
        case_sensitive: Annotated[
            bool, Field(description="Match `pattern` case-sensitively (default: case-insensitive).")
        ] = False,
        include: Annotated[
            list[str] | None, Field(description="Only search files matching these glob patterns, e.g. '*.py'.")
        ] = None,
        exclude: Annotated[
            list[str] | None, Field(description="Exclude files matching these glob patterns.")
        ] = None,
        exclude_dir: Annotated[
            list[str] | None, Field(description="Exclude directories by name or glob, e.g. 'node_modules'.")
        ] = None,
        limit: Annotated[
            int | None,
            Field(
                ge=1,
                description="Max hits; pass null for exhaustive (exhaustive only works with `pattern` set).",
            ),
        ] = 15,
        code_only: Annotated[bool, Field(description="Only search code files, skipping docs/config.")] = False,
        semantic_only: Annotated[bool, Field(description="Disable keyword matching; pure semantic ranking.")] = False,
        alpha: Annotated[
            float | None,
            Field(ge=0.0, le=1.0, description="Hybrid balance from 0.0 (keyword) to 1.0 (semantic); default 0.6."),
        ] = None,
        snippet_lines: Annotated[
            int, Field(ge=0, description="Lines of code shown per hit in the text listing (default 6).")
        ] = 6,
        include_code: Annotated[
            bool, Field(description="Include each hit's full source in structured_content.")
        ] = False,
        skip_index_update: Annotated[
            bool, Field(description="Skip colgrep's automatic index refresh before searching.")
        ] = False,
    ) -> CallToolResult:
        """Ranked semantic + hybrid search over code units (functions, classes, docs).

        Prefer this over shell grep for any question about what, where or how
        code does something. Pass `pattern` (a regex) to narrow via hybrid
        keyword+semantic ranking when you know an identifier; omit `limit`
        for an exhaustive listing. Each hit carries a `hit_id` — pass it to
        `expand` to read the full source instead of opening the whole file.
        """
        settings = get_settings(ctx)
        result, _hits = await _do_search(
            ctx,
            query=query,
            paths=paths,
            pattern=pattern,
            fixed_string=fixed_string,
            whole_word=whole_word,
            case_sensitive=case_sensitive,
            include=include,
            exclude=exclude,
            exclude_dir=exclude_dir,
            limit=limit,
            code_only=code_only,
            semantic_only=semantic_only,
            alpha=alpha,
            skip_index_update=skip_index_update,
            snippet_lines=snippet_lines,
            include_code=include_code,
        )

        text, capped = render_search_text(result, settings.text_budget)
        if capped:
            result.truncated = True
            result.notes.append(note(Code.TEXT_TRUNCATED, "text listing was capped by the token budget"))
            await safe_log(
                ctx, "warning", f"search text truncated to {settings.text_budget} chars; see structured_content for all hits"
            )

        return CallToolResult(content=[TextContent(type="text", text=text)], structured_content=result.model_dump())

    @mcp.tool(
        title="Find files",
        annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False),
    )
    async def find_files(
        ctx: Context,
        query: Annotated[str, Field(description="Natural-language description of the behaviour you are looking for.")],
        paths: Annotated[
            list[str] | None, Field(description="Files/directories to search (default: the project root).")
        ] = None,
        pattern: Annotated[
            str | None,
            Field(description="Regex pre-filter (hybrid mode): only units whose text matches are ranked."),
        ] = None,
        include: Annotated[
            list[str] | None, Field(description="Only search files matching these glob patterns, e.g. '*.py'.")
        ] = None,
        exclude: Annotated[
            list[str] | None, Field(description="Exclude files matching these glob patterns.")
        ] = None,
        exclude_dir: Annotated[
            list[str] | None, Field(description="Exclude directories by name or glob, e.g. 'node_modules'.")
        ] = None,
        limit: Annotated[
            int | None,
            Field(
                ge=1,
                description="Max files; pass null for exhaustive (exhaustive only works with `pattern` set).",
            ),
        ] = 15,
    ) -> CallToolResult:
        """Which files are about a topic — ranked, deduplicated file list instead of individual hits.

        Use before an edit to see everywhere a concept lives, or when a list
        of files is more useful than code snippets. `query` drives ranking;
        add `pattern` to narrow via hybrid search.
        """
        settings = get_settings(ctx)
        hit_limit = min(limit * 3, 300) if limit is not None else None
        result, hits = await _do_search(
            ctx,
            query=query,
            paths=paths,
            pattern=pattern,
            fixed_string=False,
            whole_word=False,
            case_sensitive=False,
            include=include,
            exclude=exclude,
            exclude_dir=exclude_dir,
            limit=hit_limit,
            code_only=False,
            semantic_only=False,
            alpha=None,
            skip_index_update=False,
            snippet_lines=0,
            include_code=False,
        )

        by_file: dict[str, FileHit] = {}
        for hit in hits:
            existing = by_file.get(hit.file)
            if existing is None:
                # Hits arrive best-score-first, so the first hit for a file sets its best_score.
                by_file[hit.file] = FileHit(file=hit.file, best_score=hit.score, hits=1, top_units=[hit.name])
            else:
                existing.hits += 1
                if len(existing.top_units) < 5:
                    existing.top_units.append(hit.name)

        all_files = list(by_file.values())
        files = all_files[:limit] if limit is not None else all_files
        was_limited = limit is not None and len(all_files) > limit

        file_result = FileResult(
            query=query,
            pattern=pattern,
            paths=result.paths,
            files=files,
            truncated=was_limited,
            elapsed_ms=result.elapsed_ms,
        )

        text, capped = render_files_text(file_result, settings.text_budget)
        if capped:
            file_result.truncated = True
            await safe_log(
                ctx,
                "warning",
                f"find_files text truncated to {settings.text_budget} chars; see structured_content for all files",
            )

        return CallToolResult(content=[TextContent(type="text", text=text)], structured_content=file_result.model_dump())

    @mcp.tool(
        title="Expand hits",
        annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False),
    )
    async def expand(
        ctx: Context,
        hit_ids: Annotated[
            list[str], Field(description="hit_id values from a search/find_files result, e.g. '/repo/a.py:10-42'.")
        ],
        max_lines: Annotated[
            int, Field(ge=1, description="Cap on lines of source read per hit (default 200).")
        ] = 200,
    ) -> CallToolResult:
        """Read the full source of hits already returned by `search`/`find_files`.

        Pass their `hit_id`s verbatim — no need to re-search. Each is read
        straight off disk at its located `[line, end_line]` span, so use this
        instead of opening a whole file to inspect the few hits that matter.
        """
        # No adapter/lock involved: expand reads the filesystem directly, so
        # `ctx` (required for MCPServer's context injection) goes unused here.
        units: list[ExpandedUnit] = []
        for hit_id in hit_ids:
            match = _HIT_ID_RE.match(hit_id)
            if not match:
                units.append(
                    ExpandedUnit(
                        hit_id=hit_id,
                        file="",
                        line=0,
                        end_line=0,
                        error=str(tool_error(Code.BAD_HIT_ID, f"malformed hit_id: {hit_id!r}")),
                    )
                )
                continue

            file, line_s, end_s = match.group(1), match.group(2), match.group(3)
            line, end_line = int(line_s), int(end_s)
            try:
                # Off the event loop (F11): a hit's file can be arbitrarily
                # large, and this handler otherwise never awaits.
                text = await asyncio.to_thread(Path(file).read_text, errors="replace")
            except OSError as exc:
                units.append(
                    ExpandedUnit(
                        hit_id=hit_id, file=file, line=line, end_line=end_line, error=f"could not read {file}: {exc}"
                    )
                )
                continue

            lines = text.splitlines()
            start_idx = max(line - 1, 0)
            end_idx = min(end_line, len(lines))
            selected = lines[start_idx:end_idx]
            was_truncated = len(selected) > max_lines
            if was_truncated:
                selected = selected[:max_lines]

            units.append(
                ExpandedUnit(
                    hit_id=hit_id,
                    file=file,
                    line=line,
                    end_line=end_line,
                    code="\n".join(selected),
                    truncated=was_truncated,
                )
            )

        def _fence(unit: ExpandedUnit) -> str:
            if unit.error:
                return f"```{unit.hit_id}\nerror: {unit.error}\n```"
            return f"```{unit.hit_id}\n{unit.code or ''}\n```"

        result = ExpandResult(units=units)
        text = "\n\n".join(_fence(unit) for unit in units)

        return CallToolResult(content=[TextContent(type="text", text=text)], structured_content=result.model_dump())
