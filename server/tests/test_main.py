"""Tests for the `colgrep-mcp` console entry point (`__main__.main`; F9)."""

from __future__ import annotations

import pytest

from colgrep_mcp.__main__ import main


def test_main_exits_2_with_a_one_line_message_on_malformed_timeout(monkeypatch, capsys):
    monkeypatch.setenv("COLGREP_MCP_TIMEOUT", "not-a-number")

    with pytest.raises(SystemExit) as exc_info:
        main([])

    assert exc_info.value.code == 2

    err = capsys.readouterr().err
    lines = [line for line in err.splitlines() if line]
    assert len(lines) == 1
    assert "COLGREP_MCP_TIMEOUT" in lines[0]
    # No raw traceback leaked to stderr as the only diagnostic.
    assert "Traceback" not in err
