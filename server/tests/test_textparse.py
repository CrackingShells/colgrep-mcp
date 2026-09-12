"""Fixture tests for the pure text parsers (R03 §Text-format samples, R05 D1/D2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from colgrep_mcp.models import IndexInfo, IndexStatus
from colgrep_mcp.textparse import (
    IndexSummary,
    parse_index_summary,
    parse_settings,
    parse_stats,
    parse_status,
)

FIXTURES = Path(__file__).parent / "fixtures" / "colgrep"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text()


class TestParseStatus:
    def test_indexed_shape(self):
        text = _read("status_indexed.txt")
        result = parse_status(text, "/private/tmp")

        assert isinstance(result, IndexStatus)
        assert result.indexed is True
        assert result.project == "/private/tmp"
        assert result.model == "lightonai/LateOn-Code-edge"
        assert result.index_path == "/Users/hacker/Library/Application Support/colgrep/indices/tmp-a825743a"
        assert result.raw == text
        assert result.requested_path == "/private/tmp"

    def test_indexed_shape_requested_path_differs_from_reported_project(self):
        # R05 D3: colgrep folds any path under an already-registered ancestor
        # project into that ancestor. The text always reports the *ancestor*
        # root ("Project: /private/tmp"), never the deeper path we asked
        # about — requested_path is the only place that survives.
        text = _read("status_indexed.txt")
        requested = "/private/tmp/some/deeper/subdir/never/asked/about/private/tmp/itself"
        result = parse_status(text, requested)

        assert result.project == "/private/tmp"
        assert result.requested_path == requested
        assert result.project != result.requested_path

    def test_missing_shape(self):
        text = _read("status_missing.txt")
        requested = "/private/var/folders/nw/ddpd99c119j47w3s4gzv7sb00000gn/T/colgrep_clear_test"
        result = parse_status(text, requested)

        assert result.indexed is False
        assert result.project == requested
        assert result.model == "lightonai/LateOn-Code-edge"
        assert result.index_path is None
        assert result.raw == text
        assert result.requested_path == requested


def test_parse_stats_full_dump():
    text = _read("stats.txt")
    infos = parse_stats(text)

    assert len(infos) == 154
    assert all(isinstance(i, IndexInfo) for i in infos)
    assert sum(i.units_indexed for i in infos) == 138402
    assert sum(i.search_count for i in infos) == 4613
    first = infos[0]
    assert first.project == "/Users/hacker/Documents/src/LittleCoinCoin/usd-bio/examples/p53_mdm2"
    assert first.model == "lightonai/LateOn-Code-edge"
    assert first.units_indexed == 649
    assert first.search_count == 3


def test_parse_settings():
    text = _read("settings.txt")
    settings = parse_settings(text)

    assert settings["model"] == "lightonai/LateOn-Code-edge (default)"
    assert settings["k"] == "25 (default)"
    assert settings["n"] == "6 (default)"
    assert settings["coreml-cache"] == "(default: ~/Library/Caches/next-plaid/coreml)"
    assert settings["force-incl"] == "(none)"
    # Footer "Use --x ..." instruction lines must not leak in as keys.
    assert not any(k.startswith("Use") for k in settings)
    assert "Current configuration" not in settings


@pytest.mark.parametrize(
    "line, expected",
    [
        (
            "Indexed /private/tmp (subdir: corpus/click) (added: 155, changed: 1, deleted: 199, unchanged: 0)",
            IndexSummary(
                root="/private/tmp",
                added=155,
                changed=1,
                deleted=199,
                unchanged=0,
                up_to_date=False,
                files=None,
            ),
        ),
        (
            "Indexed /private/var/folders/x/colgrep_clear_test (added: 1, changed: 0, deleted: 0, unchanged: 0)",
            IndexSummary(
                root="/private/var/folders/x/colgrep_clear_test",
                added=1,
                changed=0,
                deleted=0,
                unchanged=0,
                up_to_date=False,
                files=None,
            ),
        ),
        (
            "Index is up to date for /private/tmp (156 files)",
            IndexSummary(
                root="/private/tmp",
                added=None,
                changed=None,
                deleted=None,
                unchanged=None,
                up_to_date=True,
                files=156,
            ),
        ),
    ],
)
def test_parse_index_summary_matches(line, expected):
    assert parse_index_summary(line) == expected


@pytest.mark.parametrize(
    "line",
    [
        "🤖 Model: lightonai/LateOn-Code-edge (CPU)",
        "📂 Building index...",
        "",
        "some unrelated stderr noise",
    ],
)
def test_parse_index_summary_none_for_other_lines(line):
    assert parse_index_summary(line) is None


def test_parse_index_summary_against_init_stderr_fixture():
    lines = _read("init_stderr.txt").splitlines()
    summaries = [s for s in (parse_index_summary(ln) for ln in lines) if s is not None]
    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.root == "/private/tmp"
    assert summary.added == 155
    assert summary.changed == 1
    assert summary.deleted == 199
    assert summary.unchanged == 0
    assert summary.up_to_date is False


def test_parse_index_summary_against_uptodate_stderr_fixture():
    lines = _read("init_uptodate_stderr.txt").splitlines()
    summaries = [s for s in (parse_index_summary(ln) for ln in lines) if s is not None]
    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.root == "/private/tmp"
    assert summary.up_to_date is True
    assert summary.files == 156
