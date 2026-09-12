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
      multiple candidates by matching the following lines (multi-line code,
      trailing whitespace ignored) or by nearest distance to `reported_line`
      (single-line code).
    - A single first-line candidate is still required to match the rest of
      `code` before being trusted.
    - Falls back to `(reported_line, reported_end, False)` when no candidate
      first line is found, when the sole first-line candidate's block
      doesn't match the rest of `code`, or when a multi-line disambiguation
      finds no full match at all.
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
        # A unique first-line match is not enough on its own: the rest of
        # `code` must actually match what follows in the file too, or a
        # stale/edited file (or a hit whose `code` simply doesn't match past
        # line 1) would come back confidently `verified=True` with a wrong
        # `end_line` (F3).
        line = candidates[0]
        if file_lines[line - 1 : line - 1 + len(code_lines)] == code_lines:
            return (line, line + len(code_lines) - 1, True)
        return (reported_line, reported_end, False)

    if len(code_lines) == 1:
        # Single-line code: no following lines to disambiguate with — prefer
        # whichever candidate colgrep's (possibly-wrong) reported_line is
        # closest to.
        line = min(candidates, key=lambda c: abs(c - reported_line))
        return (line, line, True)

    # Multi-line code: disambiguate by matching the full block of lines,
    # trailing-whitespace-normalised (F4). A strict-equality comparison can
    # find a *unique* full match that is nevertheless the wrong occurrence —
    # e.g. two same-first-line candidates where only the reported-line-
    # adjacent one differs from `code` by trailing whitespace on a later
    # line; strict equality excludes exactly that one, silently leaving the
    # unrelated occurrence as the sole "unique full match". Normalising both
    # sides before comparing only ever admits candidates a strict comparison
    # would also admit, plus ones differing solely by trailing whitespace, so
    # it can only recover matches, never introduce a false one for lines that
    # actually differ in content.
    full_matches = _full_matches(candidates, file_lines, code_lines)

    if len(full_matches) == 1:
        line = full_matches[0]
        return (line, line + len(code_lines) - 1, True)
    if len(full_matches) > 1:
        # Still ambiguous (identical duplicated blocks) — nearest reported
        # location is the best remaining signal.
        line = min(full_matches, key=lambda c: abs(c - reported_line))
        return (line, line + len(code_lines) - 1, True)

    # None of the same-first-line candidates match the rest of the block,
    # even after tolerating trailing whitespace.
    return (reported_line, reported_end, False)


def _full_matches(candidates: list[int], file_lines: list[str], code_lines: list[str]) -> list[int]:
    """Candidates whose full block matches `code_lines`, trailing whitespace
    ignored per line (F4: a whitespace-only difference on a non-first line
    must not exclude the otherwise-correct occurrence)."""

    def _norm(lines: list[str]) -> list[str]:
        return [line.rstrip() for line in lines]

    target = _norm(code_lines)
    return [c for c in candidates if _norm(file_lines[c - 1 : c - 1 + len(code_lines)]) == target]
