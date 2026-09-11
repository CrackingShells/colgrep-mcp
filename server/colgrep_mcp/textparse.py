"""Pure text parsers for colgrep's non-JSON subcommands (`status`, `--stats`, `settings`,
init/clear progress lines).

Implemented in leaf `colgrep_adapter` against fixtures captured in R03/R05
(`tests/fixtures/colgrep/`). Every function here is a pure string -> data
transform: no subprocess, no I/O, so parsing bugs are isolated from process
bugs (adapter.py owns the subprocess).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import IndexInfo, IndexStatus

# --- status -----------------------------------------------------------------

# "No index found for <path> [<model>]" (colgrep has never indexed this path,
# or more precisely: no already-registered ancestor project covers it).
_STATUS_MISSING_RE = re.compile(r"^No index found for (?P<project>.+?) \[(?P<model>.+?)\]\s*$", re.MULTILINE)

# "Project: <path>" / "Model:   <id>" / "Index:   <path>" — one per line, no
# leading indent (the optional "  Subdirectory: ..." line that sometimes
# follows "Project:" is deliberately ignored: it is not part of any model).
_STATUS_PROJECT_RE = re.compile(r"^Project:\s*(?P<project>.+)$", re.MULTILINE)
_STATUS_MODEL_RE = re.compile(r"^Model:\s*(?P<model>.+)$", re.MULTILINE)
_STATUS_INDEX_RE = re.compile(r"^Index:\s*(?P<index_path>.+)$", re.MULTILINE)


def parse_status(text: str, project: str) -> IndexStatus:
    """Parse `colgrep status <path>` output.

    `project` is the path the caller invoked `status` with; it always becomes
    `IndexStatus.requested_path` verbatim (and is the fallback for `.project`
    if the text cannot be parsed, though that should never happen for either
    known shape). `.project` itself is the root colgrep *reports* in the
    text, which can differ from `project` (R05 D3: colgrep folds a path into
    the nearest already-registered ancestor project). `raw` always carries
    the untouched text.
    """
    missing = _STATUS_MISSING_RE.search(text)
    if missing:
        return IndexStatus(
            project=missing.group("project").strip(),
            indexed=False,
            model=missing.group("model").strip(),
            index_path=None,
            units_indexed=None,
            search_count=None,
            raw=text,
            requested_path=project,
        )

    project_m = _STATUS_PROJECT_RE.search(text)
    model_m = _STATUS_MODEL_RE.search(text)
    index_m = _STATUS_INDEX_RE.search(text)
    return IndexStatus(
        project=project_m.group("project").strip() if project_m else project,
        indexed=project_m is not None,
        model=model_m.group("model").strip() if model_m else None,
        index_path=index_m.group("index_path").strip() if index_m else None,
        units_indexed=None,
        search_count=None,
        raw=text,
        requested_path=project,
    )


# --- stats --------------------------------------------------------------

# Repeating block: "Project: <path>" then indented "Model:", "Functions
# indexed:", "Search count:" lines. `finditer` skips over the blank-line
# separators and the trailing "Total: ..." line unconditionally.
_STATS_BLOCK_RE = re.compile(
    r"Project:\s*(?P<project>.+?)\n"
    r"[ \t]*Model:\s*(?P<model>.+?)\n"
    r"[ \t]*Functions indexed:\s*(?P<units>\d+)\n"
    r"[ \t]*Search count:\s*(?P<search>\d+)"
)


def parse_stats(text: str) -> list[IndexInfo]:
    """Parse `colgrep --stats` (machine-global, one block per project)."""
    return [
        IndexInfo(
            project=m.group("project").strip(),
            model=m.group("model").strip(),
            units_indexed=int(m.group("units")),
            search_count=int(m.group("search")),
        )
        for m in _STATS_BLOCK_RE.finditer(text)
    ]


# --- settings -----------------------------------------------------------

# "  key:  value (note)" — exactly two leading spaces distinguishes a config
# line from the zero-indent header ("Current configuration:") and the
# zero-indent trailing "Use --x to ..." instruction lines.
_SETTINGS_LINE_RE = re.compile(r"^  ([A-Za-z][\w-]*):\s*(.*)$")


def parse_settings(text: str) -> dict[str, str]:
    """Parse `colgrep settings`; the parenthetical note stays inside the value."""
    result: dict[str, str] = {}
    for line in text.splitlines():
        m = _SETTINGS_LINE_RE.match(line)
        if m:
            result[m.group(1)] = m.group(2).strip()
    return result


# --- index build/refresh summary line -----------------------------------


@dataclass
class IndexSummary:
    """Parsed form of colgrep's one-line indexing summary (R05 D2)."""

    root: str
    added: int | None = None
    changed: int | None = None
    deleted: int | None = None
    unchanged: int | None = None
    up_to_date: bool = False
    files: int | None = None


_SUMMARY_INDEXED_RE = re.compile(
    r"^Indexed (?P<root>.+?)(?: \(subdir: .*?\))? "
    r"\(added: (?P<added>\d+), changed: (?P<changed>\d+), "
    r"deleted: (?P<deleted>\d+), unchanged: (?P<unchanged>\d+)\)$"
)
_SUMMARY_UPTODATE_RE = re.compile(r"^Index is up to date for (?P<root>.+?) \((?P<files>\d+) files?\)$")


def parse_index_summary(line: str) -> IndexSummary | None:
    """Parse one stderr line; `None` for anything that is not a summary line.

    colgrep's indexing stderr carries no per-file progress (R05 D2): only a
    model/build banner and this one summary line, in one of two shapes.
    """
    line = line.strip()

    m = _SUMMARY_INDEXED_RE.match(line)
    if m:
        return IndexSummary(
            root=m.group("root"),
            added=int(m.group("added")),
            changed=int(m.group("changed")),
            deleted=int(m.group("deleted")),
            unchanged=int(m.group("unchanged")),
            up_to_date=False,
            files=None,
        )

    m = _SUMMARY_UPTODATE_RE.match(line)
    if m:
        return IndexSummary(
            root=m.group("root"),
            up_to_date=True,
            files=int(m.group("files")),
        )

    return None
