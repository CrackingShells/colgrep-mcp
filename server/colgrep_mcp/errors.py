"""Coded errors and hints (R01 §Error model): a standardized tool-call error
code that can point an agent toward a different usage pattern.

This is the *only* module that owns the vocabulary. Every `ToolError` a tool
raises deliberately, and every degraded-success note a tool appends to
`SearchResult.notes`, is built through `tool_error`/`note` so an agent can
recover by matching a stable `[CODE]` prefix instead of parsing prose. A
`ToolError` message additionally always ends with `Next: <hint>` so the next
usage pattern is visible without a second round-trip; a `note` only carries
that trailing hint when no situational `detail` is given — the full catalogue
is always available at the `colgrep://errors` resource (see `resources.py`).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import StrEnum
from pathlib import Path

from mcp.server.mcpserver.exceptions import ToolError

from .adapter import ColgrepError, ColgrepFailed, ColgrepNotFound, ColgrepParseError, ColgrepTimeout


class Code(StrEnum):
    """Stable, machine-readable failure/degradation codes (R01 §Error model)."""

    NO_HITS = "NO_HITS"
    LIMIT_DEFAULT_APPLIED = "LIMIT_DEFAULT_APPLIED"
    TEXT_TRUNCATED = "TEXT_TRUNCATED"
    LOCATION_UNVERIFIED = "LOCATION_UNVERIFIED"
    INDEX_COLD = "INDEX_COLD"
    PATH_NOT_FOUND = "PATH_NOT_FOUND"
    PROJECT_ROOT_MISMATCH = "PROJECT_ROOT_MISMATCH"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    COLGREP_MISSING = "COLGREP_MISSING"
    COLGREP_FAILED = "COLGREP_FAILED"
    COLGREP_TIMEOUT = "COLGREP_TIMEOUT"
    BAD_HIT_ID = "BAD_HIT_ID"
    INDEX_STORE_UNKNOWN = "INDEX_STORE_UNKNOWN"


#: One imperative sentence per code, naming the tool/argument to reach for next.
#: Rendered verbatim by `colgrep://errors` (`resources.errors_resource`) and
#: linked from `guide.md`'s "Codes" section.
#:
#: `INDEX_COLD` is reserved: a mapper cannot cheaply know whether a path is
#: indexed (that would cost a second `status` round-trip per failure), so
#: `from_adapter_error` never raises it itself — a `ColgrepTimeout` is always
#: surfaced as `COLGREP_TIMEOUT`, whose hint already says to call
#: `index_build` first. `INDEX_COLD` stays available for any future
#: `index_status`-driven advice that *does* know the index state cheaply.
HINTS: dict[Code, str] = {
    Code.NO_HITS: "Drop `pattern`/`include`, rephrase the query as behaviour, or widen `paths`.",
    Code.LIMIT_DEFAULT_APPLIED: "Pass an explicit larger `limit`, or add `pattern` for an exhaustive result.",
    Code.TEXT_TRUNCATED: "Read `structured_content` for all hits; call `expand` on the `hit_id`s you need.",
    Code.LOCATION_UNVERIFIED: "Cite the file, not the line; `expand` the hit before quoting.",
    Code.INDEX_COLD: "Call `index_build` on the path first, then retry.",
    Code.PATH_NOT_FOUND: "Check the path; relative paths resolve against the default root shown by `doctor`.",
    Code.PROJECT_ROOT_MISMATCH: "Call again with `path` set to the reported project root.",
    Code.CONFIRMATION_REQUIRED: "Call again with `confirm=true`.",
    Code.COLGREP_MISSING: "Install colgrep (`cargo install colgrep`) or set `COLGREP_MCP_BINARY`; run `doctor`.",
    Code.COLGREP_FAILED: "Read the stderr tail; run `doctor`; retry with simpler arguments.",
    Code.COLGREP_TIMEOUT: "Call `index_build` on the path first, then retry.",
    Code.BAD_HIT_ID: "Use `hit_id` values exactly as returned by `search`: `<abs file>:<line>-<end_line>`.",
    Code.INDEX_STORE_UNKNOWN: "Run `index_build` on a project that exists on disk so the store can be located; retry.",
}


def _format(code: Code, detail: str) -> str:
    return f"[{code}] {detail} Next: {HINTS[code]}"


def tool_error(code: Code, detail: str) -> ToolError:
    """Build a `ToolError` shaped `[CODE] <detail> Next: <hint>`."""
    return ToolError(_format(code, detail))


def note(code: Code, detail: str = "") -> str:
    """Build a `SearchResult.notes` (or `FileResult.notes`) entry shaped `[CODE] ...`.

    With `detail` omitted, the note *is* the code's own hint text, so the
    coded shape and the "next step" collapse into one short string; with a
    `detail`, the situational fact is what is surfaced and the hint stays one
    lookup away at `colgrep://errors`.
    """
    return f"[{code}] {detail or HINTS[code]}"


def from_adapter_error(exc: ColgrepError, *, path: Path | None = None) -> ToolError:
    """Map an adapter failure onto a coded `ToolError` (R01 §Error model; R05 D6).

    `path` is the resolved target the call was operating on, when the caller
    has one handy; it is folded into the detail so the message still names
    the path even though `exc.argv`/`exc.stderr_tail` usually do too.
    """
    where = f" ({path})" if path is not None else ""

    if isinstance(exc, ColgrepNotFound):
        return tool_error(Code.COLGREP_MISSING, f"colgrep not found on PATH: {exc}")

    if isinstance(exc, ColgrepTimeout):
        # A mapper cannot cheaply tell whether `path` is indexed (see the
        # `INDEX_COLD` note on `HINTS` above) — always `COLGREP_TIMEOUT`,
        # whose own hint already names `index_build`.
        return tool_error(Code.COLGREP_TIMEOUT, f"{exc}{where}")

    if isinstance(exc, ColgrepFailed):
        tail = "\n".join(exc.stderr_tail.splitlines()[-20:])
        if "Path does not exist" in exc.stderr_tail:
            # colgrep's own stderr already spells out the closest existing
            # directory and its contents (R05 D6) — keep that verbatim.
            return tool_error(Code.PATH_NOT_FOUND, f"colgrep exited {exc.returncode}{where}: {tail}")
        return tool_error(Code.COLGREP_FAILED, f"colgrep exited {exc.returncode} running {' '.join(exc.argv)}: {tail}")

    if isinstance(exc, ColgrepParseError):
        return tool_error(Code.COLGREP_FAILED, f"colgrep output could not be parsed: {exc}")

    return tool_error(Code.COLGREP_FAILED, str(exc))  # pragma: no cover - defensive, no other ColgrepError subclass


@asynccontextmanager
async def translate_adapter_errors(path: Path | None = None) -> AsyncIterator[None]:
    """Re-raise any `ColgrepError` escaping the body as the coded `ToolError` from `from_adapter_error`.

    The one place a tool wraps an adapter call. It catches the *base* class on
    purpose: the adapter's own argument guards (a query starting with `-`, a
    relative path) raise bare `ColgrepError`, and a tool that only caught the
    four subclasses let those surface as the SDK's uncoded generic error
    instead of `[COLGREP_FAILED] … Next: …`.
    """
    try:
        yield
    except ColgrepError as exc:
        raise from_adapter_error(exc, path=path) from exc
