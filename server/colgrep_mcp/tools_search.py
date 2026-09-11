"""Tool module `tools_search`: `search`, `find_files`, `expand` (R01 §Tools).

Step 1 provides the pure helpers the three tool handlers compose: converting
a raw colgrep hit into a `SearchHit` (re-locating its true source lines per
R05 D1), and rendering `SearchResult`/`FileResult` into the compact,
token-budgeted text shown to the model (R01 §Token-budget invariant).
"""

from __future__ import annotations

from pathlib import Path

from mcp.server import MCPServer

from .adapter import RawHit
from .locate import locate_unit
from .models import FileHit, FileResult, SearchHit, SearchResult


def hit_from_raw(raw: RawHit, snippet_lines: int, include_code: bool, file_cache: dict[str, str]) -> SearchHit:
    """Build a `SearchHit` from one raw colgrep JSON hit (`{"unit": {...}, "score": ...}`).

    Re-derives `line`/`end_line` via `locate_unit` (R05 D1: colgrep's reported
    values are frequently wrong) so `hit_id` is built from trustworthy
    locations. The unit's file is read at most once per `file_cache` (shared
    across a whole `search`/`find_files` call); an unreadable file degrades to
    an empty text, which makes `locate_unit` fall back to the reported
    line/end_line with `verified=False` rather than raise.

    Tolerant of missing/None optional fields (R03 §Hit JSON Schema): only
    `unit`/`score` are assumed present, everything else defaults to an empty
    string or `None`.
    """
    unit = raw.get("unit") or {}
    score = float(raw.get("score") or 0.0)
    file = unit.get("file") or ""
    code = unit.get("code") or ""
    reported_line = int(unit.get("line") or 1)
    reported_end = int(unit.get("end_line") or reported_line)

    if file not in file_cache:
        try:
            file_cache[file] = Path(file).read_text(errors="replace")
        except OSError:
            file_cache[file] = ""
    file_text = file_cache[file]

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
    whose block would push the text past `budget`. When hits were dropped,
    appends a `[K more hits ...]` continuation note (always emitted in full,
    even if it pushes slightly past `budget`: the agent needs it to know more
    exists). Trailing `result.notes` (e.g. R05 D5's exhaustive-search caveat)
    are always appended last, so a zero-hit result still renders them.

    Returns `(text, was_capped)`; `was_capped` reflects only this rendering
    step, not `result.truncated` (which may already be true upstream).
    """
    text = _search_header(result)
    capped = False
    emitted = 0
    for hit in result.hits:
        candidate = f"{text}\n{_hit_block(hit)}"
        if len(candidate) > budget:
            capped = True
            break
        text = candidate
        emitted += 1

    remaining = len(result.hits) - emitted
    if capped and remaining > 0:
        text = f"{text}\n[{remaining} more hits in structured_content; call expand(hit_ids=[...]) for code]"

    for note in result.notes:
        text = f"{text}\n{note}"

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
    """`find_files` counterpart of `render_search_text`: one line per file, same capping rule."""
    text = _files_header(result)
    capped = False
    emitted = 0
    for file_hit in result.files:
        candidate = f"{text}\n{_file_block(file_hit)}"
        if len(candidate) > budget:
            capped = True
            break
        text = candidate
        emitted += 1

    remaining = len(result.files) - emitted
    if capped and remaining > 0:
        text = f"{text}\n[{remaining} more files in structured_content]"

    return text, capped


def register(mcp: MCPServer) -> None:  # pragma: no cover - stub, implemented in Step 2
    """Attach `search`, `find_files` and `expand` to the server."""
