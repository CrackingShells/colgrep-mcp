"""Tests for `Settings.from_env` (R01 §Configuration; F9: malformed numeric
env values must fail with a readable message, not a raw `ValueError` whose
only diagnostic is a traceback)."""

from __future__ import annotations

import pytest

from colgrep_mcp.config import Settings


def test_from_env_defaults():
    settings = Settings.from_env({})
    assert settings.binary == "colgrep"
    assert settings.timeout_s == 600.0
    assert settings.text_budget == 12_000


def test_from_env_malformed_timeout_raises_readable_value_error():
    with pytest.raises(ValueError, match="COLGREP_MCP_TIMEOUT"):
        Settings.from_env({"COLGREP_MCP_TIMEOUT": "abc"})


def test_from_env_malformed_text_budget_raises_readable_value_error():
    with pytest.raises(ValueError, match="COLGREP_MCP_TEXT_BUDGET"):
        Settings.from_env({"COLGREP_MCP_TEXT_BUDGET": "not-a-number"})


def test_from_env_valid_numeric_values_still_parse():
    settings = Settings.from_env({"COLGREP_MCP_TIMEOUT": "30", "COLGREP_MCP_TEXT_BUDGET": "5000"})
    assert settings.timeout_s == 30.0
    assert settings.text_budget == 5000
