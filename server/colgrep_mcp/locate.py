"""Locate a colgrep unit's real line span inside its file (R05 D1).

colgrep's own `unit.line`/`unit.end_line` are frequently wrong (see
`__reports__/colgrep_mcp/01-findings_colgrep_behaviour_v0.md` §Contradictions:
roughly 60% of sampled hits had a bogus `line`, and `end_line` often lands
near the file's total line count instead of the unit's real closing line).
`unit.code` was observed correct in every case, so we re-derive the location
by finding `code`'s first line verbatim in the file.
"""

from __future__ import annotations


def split_lines(text: str) -> list[str]:
    """`text`'s lines, broken on `\\n` alone, with only the final empty element dropped.

    colgrep numbers lines by `\\n` (Rust `lines()`), and `expand` reads a hit's
    range the same way, so every range derived here must too. `str.splitlines`
    also breaks on `\\r`, form feed, vertical tab, `\\x1c`-`\\x1e`, NEL and U+2028/9,
    which shifts every later line of a file holding one. A `\\r` stays on its
    line; `rstripped` is how comparisons ignore it.
    """
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    return lines


def locate_unit(file_text: str, code: str, reported_line: int, reported_end: int) -> tuple[int, int, bool]:
    """Return `(line, end_line, verified)`, 1-indexed.

    - Match of `code`'s first line against the file (trailing whitespace
      ignored, so a CRLF `code` still matches), disambiguating
      multiple candidates by matching the following lines (multi-line code,
      trailing whitespace ignored) or by nearest distance to `reported_line`
      (single-line code).
    - A single first-line candidate is still required to match the rest of
      `code` before being trusted. Lines break on `\\n` alone (`split_lines`).
    - Falls back to `(reported_line, reported_end, False)` when no candidate
      first line is found, when the sole first-line candidate's block
      doesn't match the rest of `code`, or when a multi-line disambiguation
      finds no full match at all.
    """
    file_lines = split_lines(file_text)
    code_lines = split_lines(code)

    if not code_lines:
        return (reported_line, reported_end, False)

    first_line = code_lines[0].rstrip()
    candidates = [i + 1 for i, line in enumerate(file_lines) if line.rstrip() == first_line]

    if not candidates:
        return (reported_line, reported_end, False)

    if len(candidates) == 1:
        # A unique first-line match is not enough on its own: the rest of
        # `code` must actually match what follows in the file too, or a
        # stale/edited file (or a hit whose `code` simply doesn't match past
        # line 1) would come back confidently `verified=True` with a wrong
        # `end_line` (F3).
        line = candidates[0]
        if rstripped(file_lines[line - 1 : line - 1 + len(code_lines)]) == rstripped(code_lines):
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


def rstripped(lines: list[str]) -> list[str]:
    """`lines` with trailing whitespace dropped from each: the one normalisation
    every comparison of a unit's `code` against file lines goes through (F4)."""
    return [line.rstrip() for line in lines]


def span_holds(line: int, end_line: int, span_lines: list[str], code_lines: list[str]) -> bool:
    """Whether the file's `span_lines`, read at `[line, end_line]`, are exactly `code_lines`.

    The cheap check behind `locate_unit`'s answer: colgrep's own range (since
    1.8.4, the unit's own, not the file's widened one) is right when it holds
    as many lines as `code` and every one matches, trailing whitespace
    ignored like `_full_matches`. A range that is shorter than the file at
    that point (`span_lines` cut by EOF), or a different length from `code`,
    never holds, so a stale index or a pre-1.8.4 binary falls through to
    `locate_unit` over the whole text. A whitespace-only edit still holds.
    """
    n = len(code_lines)
    return (
        n > 0 and end_line - line + 1 == n and len(span_lines) == n and rstripped(span_lines) == rstripped(code_lines)
    )


def _full_matches(candidates: list[int], file_lines: list[str], code_lines: list[str]) -> list[int]:
    """Candidates whose full block matches `code_lines`, trailing whitespace
    ignored per line (F4: a whitespace-only difference on a non-first line
    must not exclude the otherwise-correct occurrence)."""
    target = rstripped(code_lines)
    return [c for c in candidates if rstripped(file_lines[c - 1 : c - 1 + len(code_lines)]) == target]
