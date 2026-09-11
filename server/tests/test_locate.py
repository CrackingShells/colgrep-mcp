"""Tests for `locate_unit` (R05 D1: colgrep's reported line/end_line are unreliable)."""

from __future__ import annotations

from colgrep_mcp.locate import locate_unit


def test_unique_match():
    file_text = "def foo():\n    return 1\n\ndef bar():\n    return 2\n"
    code = "def bar():\n    return 2"

    line, end_line, verified = locate_unit(file_text, code, reported_line=1, reported_end=1)

    assert (line, end_line, verified) == (4, 5, True)


def test_duplicate_first_lines_disambiguated():
    file_text = "def helper():\n    return 'a'\n\ndef helper():\n    return 'b'\n"
    code = "def helper():\n    return 'b'"

    line, end_line, verified = locate_unit(file_text, code, reported_line=1, reported_end=1)

    assert (line, end_line, verified) == (4, 5, True)


def test_single_line_code_prefers_nearest_to_reported_line():
    file_text = "x = 1\ny = 2\nx = 1\nz = 3\n"
    code = "x = 1"

    line, end_line, verified = locate_unit(file_text, code, reported_line=3, reported_end=3)

    assert (line, end_line, verified) == (3, 3, True)

    # Same duplicate, but reported_line points at the first candidate this time.
    line, end_line, verified = locate_unit(file_text, code, reported_line=1, reported_end=1)
    assert (line, end_line, verified) == (1, 1, True)


def test_not_found_falls_back_to_reported():
    file_text = "def foo():\n    return 1\n"
    code = "def does_not_exist():\n    pass"

    line, end_line, verified = locate_unit(file_text, code, reported_line=10, reported_end=12)

    assert (line, end_line, verified) == (10, 12, False)


def test_single_candidate_does_not_verify_when_the_rest_of_the_block_diverges():
    """F3: a unique first-line candidate must still be checked against the
    rest of `code` before being trusted — an edited/stale file (or a hit
    whose `code` doesn't match past line 1) must not come back verified."""
    file_text = "def foo():\n    return 1\n"
    code = "def foo():\n    return 2\n    extra_line_that_does_not_exist"

    line, end_line, verified = locate_unit(file_text, code, reported_line=1, reported_end=2)

    assert verified is False
    assert (line, end_line) == (1, 2)


def test_single_candidate_verifies_when_the_full_block_matches():
    file_text = "def foo():\n    return 1\n"
    code = "def foo():\n    return 1"

    line, end_line, verified = locate_unit(file_text, code, reported_line=1, reported_end=1)

    assert (line, end_line, verified) == (1, 2, True)


def test_multi_candidate_tolerates_trailing_whitespace_mismatch():
    """F4: the occurrence nearest `reported_line` differs from `code` only by
    trailing whitespace on its second line; a strict-equality full-block
    comparison excludes it, wrongly leaving the other (unrelated) occurrence
    as the sole "unique full match". Retrying with trailing whitespace
    normalised must recover the correct, reported-line-adjacent occurrence."""
    file_text = "def foo():\n    pass\n\ndef foo():\n    pass  \n"
    code = "def foo():\n    pass"

    line, end_line, verified = locate_unit(file_text, code, reported_line=4, reported_end=5)

    assert (line, end_line, verified) == (4, 5, True)


def test_crlf_file():
    file_text = "def foo():\r\n    return 1\r\n\r\ndef bar():\r\n    return 2\r\n"
    code = "def bar():\n    return 2"

    line, end_line, verified = locate_unit(file_text, code, reported_line=1, reported_end=1)

    assert (line, end_line, verified) == (4, 5, True)
