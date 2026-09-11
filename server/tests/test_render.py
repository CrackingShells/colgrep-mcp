"""Tests for the Step 1 pure helpers in `tools_search` (R01 §Token-budget invariant,
R05 D1 `hit_id`/`location_verified`)."""

from __future__ import annotations

from colgrep_mcp.models import FileHit, FileResult, SearchHit, SearchResult
from colgrep_mcp.tools_search import (
    _file_block,
    _files_header,
    _hit_block,
    _search_header,
    hit_from_raw,
    render_files_text,
    render_search_text,
)

# --- hit_from_raw ------------------------------------------------------------


def _raw_hit(**unit_overrides) -> dict:
    unit = {
        "name": "parse_config",
        "qualified_name": "src/config.py::parse_config",
        "file": "/nonexistent/src/config.py",
        "line": 1,
        "end_line": 999,
        "language": "python",
        "unit_type": "function",
        "signature": "def parse_config(path: str) -> dict",
        "code": "def parse_config(path: str) -> dict:\n    return {}\n",
    }
    unit.update(unit_overrides)
    return {"unit": unit, "score": 1.25}


def test_hit_from_raw_locates_true_lines_when_file_readable(tmp_path):
    target = tmp_path / "config.py"
    target.write_text("x = 1\n\ndef parse_config(path: str) -> dict:\n    return {}\n")
    raw = _raw_hit(file=str(target), line=1, end_line=1)  # reported values are wrong (R05 D1)

    hit = hit_from_raw(raw, snippet_lines=6, include_code=False, file_cache={})

    assert (hit.line, hit.end_line, hit.location_verified) == (3, 4, True)
    assert hit.hit_id == f"{target}:3-4"


def test_hit_from_raw_falls_back_when_file_unreadable():
    raw = _raw_hit(line=7, end_line=9)

    hit = hit_from_raw(raw, snippet_lines=6, include_code=False, file_cache={})

    assert (hit.line, hit.end_line, hit.location_verified) == (7, 9, False)
    assert hit.hit_id == "/nonexistent/src/config.py:7-9"


def test_hit_from_raw_reads_each_file_at_most_once_via_cache(tmp_path):
    target = tmp_path / "config.py"
    target.write_text("def parse_config(path: str) -> dict:\n    return {}\n")
    raw = _raw_hit(file=str(target), line=99, end_line=99)

    file_cache: dict[str, str] = {}
    hit_from_raw(raw, snippet_lines=6, include_code=False, file_cache=file_cache)
    assert str(target) in file_cache

    # Mutate the cache in place: a second call must trust the cache, not re-read
    # the (now-deleted) file from disk.
    target.unlink()
    file_cache[str(target)] = "def parse_config(path: str) -> dict:\n    return {}\n"
    hit = hit_from_raw(raw, snippet_lines=6, include_code=False, file_cache=file_cache)
    assert (hit.line, hit.location_verified) == (1, True)


def test_hit_from_raw_snippet_truncated_and_code_gated():
    raw = _raw_hit(code="line1\nline2\nline3\nline4\n")

    hit = hit_from_raw(raw, snippet_lines=2, include_code=False, file_cache={})
    assert hit.snippet == "line1\nline2"
    assert hit.code is None

    hit_full = hit_from_raw(raw, snippet_lines=2, include_code=True, file_cache={})
    assert hit_full.code == "line1\nline2\nline3\nline4\n"


def test_hit_from_raw_tolerant_of_missing_optional_fields():
    raw = {"unit": {"file": "/nonexistent/a.py"}, "score": 0.5}

    hit = hit_from_raw(raw, snippet_lines=6, include_code=False, file_cache={})

    assert hit.name == ""
    assert hit.signature is None
    assert hit.snippet is None
    assert hit.location_verified is False


# --- render_search_text --------------------------------------------------


def _hit(n: int) -> SearchHit:
    return SearchHit(
        hit_id=f"/proj/f{n}.py:{n}-{n}",
        file=f"/proj/f{n}.py",
        line=n,
        end_line=n,
        name=f"unit_{n}",
        qualified_name=f"f{n}.py::unit_{n}",
        unit_type="function",
        language="python",
        signature=f"def unit_{n}()",
        score=1.0,
        snippet=f"def unit_{n}():\n    pass",
    )


def _result(hits: list[SearchHit], notes: list[str] | None = None) -> SearchResult:
    return SearchResult(
        query="config parsing",
        pattern=None,
        paths=["/proj"],
        hits=hits,
        total=len(hits),
        truncated=False,
        elapsed_ms=12,
        notes=notes or [],
    )


def test_render_search_text_includes_header_and_hit_block_uncapped():
    result = _result([_hit(1)])

    text, capped = render_search_text(result, budget=10_000)

    assert capped is False
    assert '1 hits for "config parsing"' in text
    assert "in /proj" in text
    assert "— 12ms" in text
    assert "/proj/f1.py:1-1  score=1.00  function unit_1 — def unit_1()" in text
    assert "  def unit_1():" in text  # snippet indented two spaces
    assert "more hits" not in text


def test_render_search_text_budget_exactly_at_boundary_includes_hit():
    result = _result([_hit(1)])
    full_text, capped = render_search_text(result, budget=10_000)
    assert capped is False

    text, capped = render_search_text(result, budget=len(full_text))

    assert capped is False
    assert text == full_text


def test_render_search_text_budget_one_over_boundary_drops_hit():
    result = _result([_hit(1)])
    full_text, _ = render_search_text(result, budget=10_000)

    text, capped = render_search_text(result, budget=len(full_text) - 1)

    assert capped is True
    assert "unit_1" not in text
    assert "[1 more hits in structured_content; call expand(hit_ids=[...]) for code]" in text


def test_render_search_text_backtracks_a_hit_so_the_note_stays_within_budget():
    """R01 §Token-budget invariant: the cap is hard, note included — a hit already
    accepted is dropped again if the continuation note would push past `budget`."""
    hits = [_hit(1), _hit(2)]
    result = _result(hits)
    header = _search_header(result)
    block1 = _hit_block(hits[0])
    note_one_more = "[1 more hits in structured_content; call expand(hit_ids=[...]) for code]"

    exact_budget = len(header) + 1 + len(block1) + 1 + len(note_one_more)
    text, capped = render_search_text(result, budget=exact_budget)
    assert capped is True
    assert "unit_1" in text and "unit_2" not in text
    assert note_one_more in text

    text2, capped2 = render_search_text(result, budget=exact_budget - 1)
    assert capped2 is True
    assert "unit_1" not in text2 and "unit_2" not in text2
    assert "[2 more hits in structured_content; call expand(hit_ids=[...]) for code]" in text2


def test_render_search_text_never_exceeds_budget_when_header_alone_fits():
    """F5: a budget that comfortably fits the header alone, but not
    header+continuation-note, must still never be exceeded — even though
    zero hits are ever emitted (so the pre-existing `emitted == 0` escape
    hatch used to append the note unconditionally)."""
    hits = [_hit(1), _hit(2), _hit(3)]
    result = _result(hits)
    header = _search_header(result)
    budget = len(header) + 5

    text, capped = render_search_text(result, budget=budget)

    assert capped is True
    assert len(text) <= budget


def test_render_search_text_zero_hits_renders_notes():
    result = _result([], notes=["no units matched; try dropping pattern/include or rephrasing"])

    text, capped = render_search_text(result, budget=10_000)

    assert capped is False
    assert '0 hits for "config parsing"' in text
    assert "no units matched; try dropping pattern/include or rephrasing" in text


def test_render_search_text_pattern_shown_in_header():
    result = SearchResult(
        query="parse",
        pattern="def .*parse",
        paths=["/proj"],
        hits=[],
        total=0,
        truncated=False,
        elapsed_ms=5,
    )

    text, _ = render_search_text(result, budget=10_000)

    assert "pattern='def .*parse'" in text


# --- render_files_text -----------------------------------------------------


def _file_hit(n: int) -> FileHit:
    return FileHit(file=f"/proj/f{n}.py", best_score=1.0, hits=n, top_units=[f"unit_{n}"])


def _file_result(files: list[FileHit]) -> FileResult:
    return FileResult(
        query="config parsing",
        pattern=None,
        paths=["/proj"],
        files=files,
        truncated=False,
        elapsed_ms=8,
    )


def test_render_files_text_uncapped():
    result = _file_result([_file_hit(1), _file_hit(2)])

    text, capped = render_files_text(result, budget=10_000)

    assert capped is False
    assert '2 files for "config parsing"' in text
    assert "/proj/f1.py  score=1.00  1 hits — unit_1" in text
    assert "/proj/f2.py  score=1.00  2 hits — unit_2" in text


def test_render_files_text_never_exceeds_budget_when_header_alone_fits():
    """F5, mirrored for `render_files_text` (same loop shape)."""
    files = [_file_hit(1), _file_hit(2), _file_hit(3)]
    result = _file_result(files)
    header = _files_header(result)
    budget = len(header) + 5

    text, capped = render_files_text(result, budget=budget)

    assert capped is True
    assert len(text) <= budget


def test_render_files_text_backtracks_a_file_so_the_note_stays_within_budget():
    files = [_file_hit(1), _file_hit(2)]
    result = _file_result(files)
    header = _files_header(result)
    block1 = _file_block(files[0])
    note_one_more = "[1 more files in structured_content]"

    exact_budget = len(header) + 1 + len(block1) + 1 + len(note_one_more)
    text, capped = render_files_text(result, budget=exact_budget)
    assert capped is True
    assert "f1.py" in text and "f2.py" not in text
    assert note_one_more in text

    text2, capped2 = render_files_text(result, budget=exact_budget - 1)
    assert capped2 is True
    assert "f1.py" not in text2 and "f2.py" not in text2
    assert "[2 more files in structured_content]" in text2
