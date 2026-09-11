"""Locate a colgrep unit's real line span inside its file (R05 D1).

colgrep's own `unit.line`/`unit.end_line` are frequently wrong (see
`__reports__/colgrep_mcp/01-findings_colgrep_behaviour_v0.md` §Contradictions:
roughly 60% of sampled hits had a bogus `line`, and `end_line` often lands
near the file's total line count instead of the unit's real closing line).
`unit.code` was observed correct in every case, so we re-derive the location
by finding `code`'s first line verbatim in the file.
"""

from __future__ import annotations


def locate_unit(file_text: str, code: str, reported_line: int, reported_end: int) -> tuple[int, int, bool]:
    """Return `(line, end_line, verified)`, 1-indexed.

    - Exact match of `code`'s first line against the file, disambiguating
      multiple candidates by matching the following lines (multi-line code)
      or by nearest distance to `reported_line` (single-line code).
    - Falls back to `(reported_line, reported_end, False)` when no candidate
      first line is found, or when a multi-line disambiguation finds no full
      match at all.
    """
    file_lines = file_text.splitlines()
    code_lines = code.splitlines()

    if not code_lines:
        return (reported_line, reported_end, False)

    first_line = code_lines[0]
    candidates = [i + 1 for i, line in enumerate(file_lines) if line == first_line]

    if not candidates:
        return (reported_line, reported_end, False)

    if len(candidates) == 1:
        line = candidates[0]
        return (line, line + len(code_lines) - 1, True)

    if len(code_lines) == 1:
        # Single-line code: no following lines to disambiguate with — prefer
        # whichever candidate colgrep's (possibly-wrong) reported_line is
        # closest to.
        line = min(candidates, key=lambda c: abs(c - reported_line))
        return (line, line, True)

    # Multi-line code: disambiguate by matching the full block of lines.
    full_matches = [
        c for c in candidates if file_lines[c - 1 : c - 1 + len(code_lines)] == code_lines
    ]
    if len(full_matches) == 1:
        line = full_matches[0]
        return (line, line + len(code_lines) - 1, True)
    if len(full_matches) > 1:
        # Still ambiguous (identical duplicated blocks) — nearest reported
        # location is the best remaining signal.
        line = min(full_matches, key=lambda c: abs(c - reported_line))
        return (line, line + len(code_lines) - 1, True)

    # None of the same-first-line candidates match the rest of the block.
    return (reported_line, reported_end, False)
