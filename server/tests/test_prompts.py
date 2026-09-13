"""Tests for `colgrep_mcp.prompts`."""

from __future__ import annotations

import asyncio

import pytest
from mcp import Client
from mcp.types import PromptReference, ResourceTemplateReference

import colgrep_mcp.prompts as prompts_module
from colgrep_mcp.server import build

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def _reset_stats_cache():
    """The 30s completion cache is module-global; keep it from leaking across tests."""
    prompts_module._stats_cache = None
    yield
    prompts_module._stats_cache = None


async def test_list_prompts_arguments(settings_env):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.list_prompts()
        by_name = {p.name: {a.name: a.required for a in (p.arguments or [])} for p in result.prompts}
        assert by_name == {
            "explore": {"question": True, "path": False},
            "locate": {"target": True, "path": False},
            "impact": {"change": True, "path": False},
            "housekeeping": {"days": False},
        }


async def test_explore_prompt_text_contract(settings_env):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.get_prompt("explore", {"question": "how does retry work?"})
        assert len(result.messages) == 1
        message = result.messages[0]
        assert message.role == "user"
        text = message.content.text
        assert "how does retry work?" in text
        assert "search(" in text
        assert "expand(hit_ids" in text
        assert "shell grep" in text
        assert "location_verified" in text
        assert "limit=None" in text and "pattern" in text


async def test_locate_and_impact_prompt_text(settings_env):
    async with Client(build(), raise_exceptions=True) as client:
        locate_result = await client.get_prompt("locate", {"target": "RateLimiter"})
        locate_text = locate_result.messages[0].content.text
        assert "RateLimiter" in locate_text
        assert "find_files" in locate_text
        assert "shell grep" in locate_text

        impact_result = await client.get_prompt("impact", {"change": "parse_config"})
        impact_text = impact_result.messages[0].content.text
        assert "parse_config" in impact_text
        assert "find_files" in impact_text
        assert "limit=None" in impact_text


async def test_prompt_scopes_calls_with_path(settings_env):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.get_prompt("explore", {"question": "q", "path": "/tmp/fake-corpus"})
        text = result.messages[0].content.text
        assert 'paths=["/tmp/fake-corpus"]' in text


async def test_completion_for_status_template_path(settings_env):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.complete(
            ResourceTemplateReference(uri="colgrep://status/{+path}"),
            {"name": "path", "value": ""},
        )
        assert set(result.completion.values) == {"tmp/fake-corpus", "tmp/other"}


async def test_completion_for_status_template_path_is_prefix_filtered(settings_env):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.complete(
            ResourceTemplateReference(uri="colgrep://status/{+path}"),
            {"name": "path", "value": "tmp/fake"},
        )
        assert result.completion.values == ["tmp/fake-corpus"]


async def test_completion_for_prompt_path_argument(settings_env):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.complete(
            PromptReference(name="explore"),
            {"name": "path", "value": "/tmp/o"},
        )
        assert result.completion.values == ["/tmp/other"]


async def test_completion_ignores_non_path_arguments(settings_env):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.complete(
            PromptReference(name="explore"),
            {"name": "question", "value": "anything"},
        )
        assert result.completion.values == []


async def test_stats_cache_is_reused_within_ttl(settings_env, monkeypatch):
    import colgrep_mcp.adapter as adapter_module

    call_count = {"n": 0}
    real_stats = adapter_module.ColgrepAdapter.stats

    async def counting_stats(self):
        call_count["n"] += 1
        return await real_stats(self)

    monkeypatch.setattr(adapter_module.ColgrepAdapter, "stats", counting_stats)

    async with Client(build(), raise_exceptions=True) as client:
        await client.complete(PromptReference(name="explore"), {"name": "path", "value": ""})
        await client.complete(PromptReference(name="locate"), {"name": "path", "value": ""})

    assert call_count["n"] == 1


async def test_completion_cache_refill_is_serialised(settings_env, monkeypatch):
    """Two completions racing past a stale/empty cache must not both call
    `stats()` — the second waiter re-checks the TTL once it holds the lock
    and finds the first waiter's refill already fresh (F10)."""
    import colgrep_mcp.adapter as adapter_module

    call_count = {"n": 0}
    real_stats = adapter_module.ColgrepAdapter.stats

    async def slow_stats(self):
        call_count["n"] += 1
        await asyncio.sleep(0.05)
        return await real_stats(self)

    monkeypatch.setattr(adapter_module.ColgrepAdapter, "stats", slow_stats)

    async with Client(build(), raise_exceptions=True) as client:
        first, second = await asyncio.gather(
            client.complete(PromptReference(name="explore"), {"name": "path", "value": ""}),
            client.complete(PromptReference(name="locate"), {"name": "path", "value": ""}),
        )

    assert call_count["n"] == 1
    assert set(first.completion.values) == {"/tmp/fake-corpus", "/tmp/other"}
    assert set(second.completion.values) == {"/tmp/fake-corpus", "/tmp/other"}


async def test_housekeeping_prompt_text_contract(settings_env):
    """index_housekeeping R01 §C7: list → dry run → confirmed prune → list again."""
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.get_prompt("housekeeping", {"days": "45"})
        text = result.messages[0].content.text
        assert result.messages[0].role == "user"
        assert text.index("list_indexes(stale_only=true)") < text.index("index_prune()")
        assert text.index("index_prune()") < text.index("index_prune(dry_run=false, confirm=true")
        assert "days=45" in text and "45+ days" in text
        assert '"cold"' in text and "failed" in text
        assert "by hand" in text


async def test_housekeeping_prompt_defaults_to_thirty_days(settings_env):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.get_prompt("housekeeping", {})
        assert "days=30" in result.messages[0].content.text
