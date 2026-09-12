"""Tool module `tools_search`: `search`, `find_files`, `expand` (R01 §Tools).

Pure helpers convert a raw colgrep hit into a `SearchHit` (re-locating its
true source lines per R05 D1) and render `SearchResult`/`FileResult` into
the compact, token-budgeted text shown to the model (R01 §Token-budget
invariant) through one shared backtracking loop, `_render_budgeted`. The
three tools are module-level handlers on top of those helpers (R01 §C5),
registered onto the shared server helpers by `register`.
"""

from __future__ import annotations

import asyncio
import itertools
import re
import time
from collections.abc import Callable
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Annotated, NamedTuple

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.types import CallToolResult, TextContent
from pydantic import Field

from .adapter import RawHit, SearchRequest
from .errors import Code, note, tool_error, translate_adapter_errors
from .locate import locate_unit
from .locks import project_lock
from .logging_utils import safe_log
from .models import ExpandedUnit, ExpandResult, FileHit, FileResult, SearchHit, SearchResult
from .paths import resolve_target_paths
from .server import READ_ONLY_TOOL, get_adapter, get_settings, register_tool

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


async def _fill_file_cache(raw_hits: list[RawHit], file_cache: dict[str, str], base_path: Path | None = None) -> None:
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
    head = (
        f"{hit.file}:{hit.line}-{hit.end_line}  score={hit.score:.2f}  "
        f"{hit.unit_type} {hit.name} — {hit.signature or ''}"
    )
    if not hit.snippet:
        return head
    indented = "\n".join(f"  {line}" for line in hit.snippet.splitlines())
    return f"{head}\n{indented}"


def _render_budgeted(
    header: str,
    blocks: list[str],
    more_note: Callable[[int], str],
    trailing_notes: list[str],
    budget: int,
) -> tuple[str, bool]:
    """Render `header` plus as many `blocks` as fit in `budget` chars, then any `trailing_notes`.

    Shared backtracking loop behind `render_search_text` and
    `render_files_text` (R01 §Token-budget invariant: "capped at N
    characters"): append `header`, then each block in order, stopping before
    any block that would push the text past `budget`. When blocks were
    dropped, a `more_note(remaining)` continuation note is appended — and the
    cap is hard, so if the note itself would overflow `budget` a
    previously-appended block is dropped to make room for it, repeatedly if
    needed, rather than let the note push the text past the limit.
    `trailing_notes` are always appended last, so an empty `blocks` still
    renders them — but the cap stays hard even then: if `budget` is too small
    to fit even the header (plus the mandatory note, plus `trailing_notes`)
    with nothing left to drop, the joined text is hard-truncated to `budget`
    characters as the last resort, rather than ever returning more than
    requested.

    Returns `(text, was_capped)`.
    """
    out = [header]
    text_len = len(header)
    capped = False
    emitted = 0

    for block in blocks:
        candidate_len = text_len + 1 + len(block)
        if candidate_len > budget:
            capped = True
            break
        out.append(block)
        text_len = candidate_len
        emitted += 1

    remaining = len(blocks) - emitted
    if capped and remaining > 0:
        # Bounded by construction: each non-appending iteration drops one
        # previously-emitted block, so this runs at most `emitted + 1` times
        # (one drop per already-emitted block, plus the final appending pass)
        # before either fitting or running out of blocks to drop.
        for _ in range(emitted + 1):
            note = more_note(remaining)
            candidate_len = text_len + 1 + len(note)
            if candidate_len <= budget or emitted == 0:
                out.append(note)
                text_len = candidate_len
                break
            dropped = out.pop()
            text_len -= len(dropped) + 1
            emitted -= 1
            remaining += 1

    text = "\n".join(out)
    for note in trailing_notes:
        text = f"{text}\n{note}"

    # Hard cap (R01 §Token-budget invariant): the backtracking above can
    # still leave `header (+ note) (+ trailing_notes)` longer than `budget`
    # when `budget` is smaller than that unavoidable minimum — hard-truncate
    # as the last resort rather than ever exceed what was requested.
    if len(text) > budget:
        text = text[:budget]
        capped = True

    return text, capped


def render_search_text(result: SearchResult, budget: int) -> tuple[str, bool]:
    """Render `result` as the compact text shown to the model, capped at `budget` chars.

    Header line, then one block per hit (`file:line-end  score  unit_type
    name — signature`, snippet indented two spaces). When hits were dropped
    to fit, a `[K more hits ...]` continuation note is appended, and trailing
    `result.notes` (e.g. R05 D5's exhaustive-search caveat) are always
    appended last — see `_render_budgeted` for the shared backtracking and
    hard-cap behaviour.

    Returns `(text, was_capped)`; `was_capped` reflects only this rendering
    step, not `result.truncated` (which may already be true upstream).
    """
    return _render_budgeted(
        _search_header(result),
        [_hit_block(hit) for hit in result.hits],
        lambda remaining: f"[{remaining} more hits in structured_content; call expand(hit_ids=[...]) for code]",
        result.notes,
        budget,
    )


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
    return _render_budgeted(
        _files_header(result),
        [_file_block(file_hit) for file_hit in result.files],
        lambda remaining: f"[{remaining} more files in structured_content]",
        [],
        budget,
    )


class _RawSearchOutcome(NamedTuple):
    """What resolving, locking and running the adapter produces, before either
    caller converts `raw_hits` into its own result shape (R01 §C6)."""

    raw_hits: list[RawHit]
    resolved: list[Path]
    elapsed_ms: int
    index_updated: bool  # R05 D7, derived from stderr chatter


async def _run_adapter_search(
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
) -> _RawSearchOutcome:
    """Shared body of `search` and `find_files`: resolve, lock, run.

    Raw-hit conversion (into `SearchHit`s or straight into `FileHit`s) is the
    caller's job — a step parameterised by what each tool actually needs
    (R01 §C6), so this stops short of it.

    `on_stderr` only collects `stderr_lines` (still needed for
    `index_updated`, R05 D7) rather than forwarding a `notifications/message`
    per line: colgrep's stderr chatter can run to several lines per call
    while the logging capability is deprecated upstream, so a client paid one
    round-trip per line for nothing an agent acts on. The one fact worth
    surfacing — the index was rebuilt, so this call's `elapsed_ms` includes a
    cold build — is sent as at most one summary notification below, only
    when `index_updated` is true (R01 §C6, a deliberate client-visible
    delta: was one notification per stderr line).

    Raises `ToolError` (via `resolve_target_paths` for a bad path, via
    `translate_adapter_errors` for an adapter failure); never a bare adapter
    exception.
    """
    resolved = await resolve_target_paths(ctx, paths)

    stderr_lines: list[str] = []

    async def on_stderr(line: str) -> None:
        stderr_lines.append(line)

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
        async with translate_adapter_errors(path=resolved[0]):
            raw_hits = await adapter.search(req)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    index_updated = any("Building index" in line for line in stderr_lines)  # R05 D7
    if index_updated:
        # One summary notification instead of one per stderr line (R01 §C6):
        # the only fact a client would otherwise have to reconstruct from N
        # lines of colgrep chatter is that the index was rebuilt.
        await safe_log(ctx, "info", "colgrep rebuilt its index before this search; elapsed_ms includes the rebuild")

    return _RawSearchOutcome(
        raw_hits=raw_hits,
        resolved=resolved,
        elapsed_ms=elapsed_ms,
        index_updated=index_updated,
    )


def _file_hits_from_raw(raw_hits: list[RawHit], base_path: Path | None) -> list[FileHit]:
    """Fold raw colgrep hits straight into `FileHit`s, one per distinct file.

    `find_files` never exposes `line`/`hit_id`, so building a `SearchHit` per
    hit via `hit_from_raw` — its `locate_unit` re-derivation and (skipped-but-
    still-costed) file-cache lookup included — is pure waste: work
    proportional to raw hits instead of the files actually returned (R01
    §C6). The file key gets the same absolute-path normalisation `hit_id`
    would have used (`_resolve_hit_file`, F13) so two hits that differ only
    in relative-vs-absolute spelling still land in the same `FileHit`; no
    `SearchHit`, `hit_id` string, snippet or `locate_unit` call is built.
    Hits arrive best-score-first (R05), so the first hit seen for a file sets
    `best_score`; `top_units` is capped at 5, same as the previous fold.
    """
    by_file: dict[str, FileHit] = {}
    for raw in raw_hits:
        unit = raw.get("unit") or {}
        file = _resolve_hit_file(unit.get("file") or "", base_path)
        score = float(raw.get("score") or 0.0)
        name = unit.get("name") or ""
        existing = by_file.get(file)
        if existing is None:
            by_file[file] = FileHit(file=file, best_score=score, hits=1, top_units=[name])
        else:
            existing.hits += 1
            if len(existing.top_units) < 5:
                existing.top_units.append(name)
    return list(by_file.values())


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
) -> SearchResult:
    """`search`'s body: run the adapter, then convert every raw hit into a
    `SearchHit` (locate, snippet, `hit_id`) via `hit_from_raw`.

    `find_files` no longer routes through here (R01 §C6): it calls
    `_run_adapter_search` directly and folds raw hits straight into
    `FileHit`s, since it never exposes `line`/`hit_id` and building a
    `SearchHit` per hit for output that gets discarded was pure waste.
    """
    outcome = await _run_adapter_search(
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
    )

    # F13: `resolved[0]` is the "first search path" a relative `unit.file`
    # (not expected from colgrep, but not guaranteed absent either) resolves
    # against.
    base_path = outcome.resolved[0]
    file_cache: dict[str, str] = {}
    await _fill_file_cache(outcome.raw_hits, file_cache, base_path=base_path)
    hits = [hit_from_raw(raw, snippet_lines, include_code, file_cache, base_path=base_path) for raw in outcome.raw_hits]

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
        paths=[str(p) for p in outcome.resolved],
        hits=hits,
        total=len(hits),
        truncated=False,
        elapsed_ms=outcome.elapsed_ms,
        index_updated=outcome.index_updated,
        notes=notes,
    )
    return result


async def search(
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
    exclude: Annotated[list[str] | None, Field(description="Exclude files matching these glob patterns.")] = None,
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
    include_code: Annotated[bool, Field(description="Include each hit's full source in structured_content.")] = False,
    skip_index_update: Annotated[
        bool, Field(description="Skip colgrep's automatic index refresh before searching.")
    ] = False,
    *,
    ctx: Context,
) -> CallToolResult:
    """Ranked semantic + hybrid search over code units (functions, classes, docs).

    Prefer this over shell grep for any question about what, where or how
    code does something. Pass `pattern` (a regex) to narrow via hybrid
    keyword+semantic ranking when you know an identifier; omit `limit`
    for an exhaustive listing. Each hit carries a `hit_id` — pass it to
    `expand` to read the full source instead of opening the whole file.
    """
    settings = get_settings(ctx)
    result = await _do_search(
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
            ctx,
            "warning",
            f"search text truncated to {settings.text_budget} chars; see structured_content for all hits",
        )

    return CallToolResult(content=[TextContent(type="text", text=text)], structured_content=result.model_dump())


async def find_files(
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
    exclude: Annotated[list[str] | None, Field(description="Exclude files matching these glob patterns.")] = None,
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
    *,
    ctx: Context,
) -> CallToolResult:
    """Which files are about a topic — ranked, deduplicated file list instead of individual hits.

    Use before an edit to see everywhere a concept lives, or when a list
    of files is more useful than code snippets. `query` drives ranking;
    add `pattern` to narrow via hybrid search.
    """
    settings = get_settings(ctx)
    hit_limit = min(limit * 3, 300) if limit is not None else None
    outcome = await _run_adapter_search(
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
    )

    # F13: `resolved[0]` is the "first search path" a relative `unit.file`
    # (not expected from colgrep, but not guaranteed absent either) resolves
    # against — same base `_file_hits_from_raw`'s file-key normalisation uses.
    all_files = _file_hits_from_raw(outcome.raw_hits, outcome.resolved[0])

    files = all_files[:limit] if limit is not None else all_files
    was_limited = limit is not None and len(all_files) > limit

    file_result = FileResult(
        query=query,
        pattern=pattern,
        paths=[str(p) for p in outcome.resolved],
        files=files,
        truncated=was_limited,
        elapsed_ms=outcome.elapsed_ms,
    )

    text, capped = render_files_text(file_result, settings.text_budget)
    if capped:
        file_result.truncated = True
        await safe_log(
            ctx,
            "warning",
            f"find_files text truncated to {settings.text_budget} chars; see structured_content for all files",
        )

    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        structured_content=file_result.model_dump(),
    )


def _strip_line_ending(line: str) -> str:
    """Remove one trailing line terminator, exactly as `str.splitlines()` would per line."""
    if line.endswith("\r\n"):
        return line[:-2]
    if line.endswith("\n") or line.endswith("\r"):
        return line[:-1]
    return line


def _read_span(file: str, line: int, end_line: int) -> list[str]:
    """Read only lines `[line, end_line]` (1-indexed, inclusive) of `file`.

    `expand` returns at most `max_lines` of a hit whose file can be
    arbitrarily large; reading the whole file with `read_text` +
    `splitlines` (the old approach) does I/O proportional to the file's
    size instead of the span actually requested. Opening the file and
    `itertools.islice`-ing its line iterator reads (and decodes) only the
    requested span. `errors="replace"` and the default text-mode encoding
    match `Path.read_text(errors="replace")`; a `line` past EOF yields `[]`,
    same as the old `lines[start_idx:end_idx]` slicing.
    """
    start_idx = max(line - 1, 0)
    end_idx = max(end_line, start_idx)
    with open(file, errors="replace") as f:
        selected = list(itertools.islice(f, start_idx, end_idx))
    return [_strip_line_ending(raw_line) for raw_line in selected]


async def expand(
    hit_ids: Annotated[
        list[str], Field(description="hit_id values from a search/find_files result, e.g. '/repo/a.py:10-42'.")
    ],
    max_lines: Annotated[int, Field(ge=1, description="Cap on lines of source read per hit (default 200).")] = 200,
    *,
    ctx: Context,
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
            selected = await asyncio.to_thread(_read_span, file, line, end_line)
        except OSError as exc:
            units.append(
                ExpandedUnit(
                    hit_id=hit_id, file=file, line=line, end_line=end_line, error=f"could not read {file}: {exc}"
                )
            )
            continue

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


def register(mcp: MCPServer) -> None:
    """Attach `search`, `find_files` and `expand` to the server."""
    register_tool(mcp, search, title="Search code", annotations=READ_ONLY_TOOL)
    register_tool(mcp, find_files, title="Find files", annotations=READ_ONLY_TOOL)
    register_tool(mcp, expand, title="Expand hits", annotations=READ_ONLY_TOOL)
