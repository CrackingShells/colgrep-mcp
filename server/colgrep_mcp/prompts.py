"""Prompts (`explore`, `locate`, `impact`) and the shared `path` completion.

R01 §Prompts / R05 D5, D11: the prompt text must say `limit=None` is
exhaustive only together with `pattern` (colgrep's own runtime default,
absent both, is 15 — not what `colgrep settings` shows for `k`), and must
forbid shell grep for the meaning-based step. Wording is kept in lockstep
with `skills/colgrep-search/SKILL.md`.

The single `@mcp.completion()` handler on the server is registered here
(`complete_path`) and answers for both the `colgrep://status/{+path}`
template's `path` variable and each prompt's `path` argument. It has no
request `Context` to fetch the lifespan's adapter through the usual route
(the SDK does not thread one into a completion callback: `func(ref, argument,
context)` carries only the completion `context`, never a request `Context`)
— it reaches the same adapter through `server.get_app()`'s module-global
handle instead (`get_adapter()`, no `ctx`), and caches the resulting project
list for 30s behind a lock so two completions racing past a stale cache don't
both spawn `colgrep --stats`.
"""

from __future__ import annotations

import asyncio
import time

from mcp.server import MCPServer
from mcp.types import Completion, CompletionArgument, CompletionContext, PromptReference, ResourceTemplateReference

from .adapter import ColgrepError
from .models import IndexInfo
from .server import get_adapter

_STATUS_TEMPLATE_URI = "colgrep://status/{+path}"
_PATH_PROMPTS = {"explore", "locate", "impact"}
_STATS_CACHE_TTL_S = 30.0

_stats_cache: tuple[float, list[IndexInfo]] | None = None
#: Serialises a stale-cache refill: two completions racing past the TTL
#: check must not both spawn `colgrep --stats` (F10).
_stats_lock = asyncio.Lock()


def _stats_cache_is_fresh() -> bool:
    return _stats_cache is not None and time.monotonic() - _stats_cache[0] < _STATS_CACHE_TTL_S


async def _cached_project_paths() -> list[str]:
    """`adapter.stats()` project paths, refreshed at most once per 30s.

    Double-checked under `_stats_lock`: a waiter that blocked on a stale
    cache re-checks the TTL once it holds the lock, since another completion
    may have already refilled it while it waited.
    """
    global _stats_cache
    if _stats_cache_is_fresh():
        return [info.project for info in _stats_cache[1]]
    async with _stats_lock:
        if _stats_cache_is_fresh():
            return [info.project for info in _stats_cache[1]]
        infos = await get_adapter().stats()
        _stats_cache = (time.monotonic(), infos)
        return [info.project for info in infos]


def _scope_clause(path: str | None) -> str:
    if path:
        return f'Scope every call below with paths=["{path}"].'
    return "No `path` was given: omit `paths` and let each tool resolve its own default root."


def _paths_kwarg(path: str | None) -> str:
    return f', paths=["{path}"]' if path else ""


def explore(question: str, path: str | None = None) -> str:
    """explore — knowledge-acquisition loop for a how/why/where question."""
    scope = _scope_clause(path)
    paths_kw = _paths_kwarg(path)
    return (
        f'Answer this question about the codebase: "{question}"\n\n'
        "This is a meaning-based question, not a literal-text lookup — never use shell "
        "grep, rg, find, or the Grep tool for it. Use only the colgrep-mcp tools below.\n"
        f"{scope}\n\n"
        f'1. search(query="{question}", limit=25{paths_kw}) — one broad pass first; read '
        "the ranked hits before doing anything else.\n"
        "2. If the real implementation is not yet named, run 1-2 narrower calls: "
        f'search(query="{question}", pattern=<identifier>, limit=10{paths_kw}).\n'
        "3. limit=None is exhaustive only together with pattern. Without pattern, omitting "
        "limit still returns colgrep's own default of 15 hits, not everything.\n"
        "4. expand(hit_ids=[...]) on at most 5 hits that actually answer the question — "
        "never open whole files instead.\n\n"
        "Output contract: cite file:line from hits whose location_verified is true. If a "
        "hit you must cite has location_verified false, say so next to that citation."
    )


def locate(target: str, path: str | None = None) -> str:
    """locate — find where a symbol/behaviour is defined and used."""
    scope = _scope_clause(path)
    paths_kw = _paths_kwarg(path)
    return (
        f'Locate where "{target}" is defined and used in this codebase.\n\n'
        "This is an identifier lookup, not a literal-text one — never use shell grep, rg, "
        "find, or the Grep tool here. Use only the colgrep-mcp tools below.\n"
        f"{scope}\n\n"
        f'1. search(query="uses of {target}", pattern="{target}", limit=15{paths_kw}) — '
        "hybrid: pattern pre-filters on the identifier, query ranks semantically.\n"
        "2. limit=None is exhaustive only together with pattern (already set here); never "
        "rely on limit=None with no pattern — that only gets colgrep's default of 15.\n"
        "3. For a file-level answer instead of unit-level hits, also run "
        f'find_files(query="uses of {target}", pattern="{target}"{paths_kw}).\n'
        f"4. expand(hit_ids=[...]) on the hits that actually define or use \"{target}\".\n\n"
        "Output contract: cite file:line from hits whose location_verified is true. If a "
        "hit you must cite has location_verified false, say so next to that citation."
    )


def impact(change: str, path: str | None = None) -> str:
    """impact — find what breaks before editing a symbol."""
    scope = _scope_clause(path)
    paths_kw = _paths_kwarg(path)
    return (
        f'Assess the impact of changing "{change}" before you edit it.\n\n'
        "Never use shell grep, rg, find, or the Grep tool for this — completeness matters "
        "here, and only colgrep-mcp's exhaustive search gives it.\n"
        f"{scope}\n\n"
        f'1. search(query="uses of {change}", pattern="{change}", limit=None{paths_kw}) — '
        "pattern is set, so limit=None is genuinely exhaustive: nothing is dropped by "
        "rank. Without pattern, limit=None only gets colgrep's default of 15 — do not "
        "rely on that here.\n"
        f'2. find_files(query="tests for {change}", pattern="{change}", '
        f'include=["*test*"]{paths_kw}) to find every test that must also change.\n'
        "3. expand(hit_ids=[...]) only on hits you are unsure about from the listing alone.\n\n"
        "Output contract: report every affected file, citing file:line from hits whose "
        "location_verified is true; note explicitly any cited hit whose location_verified "
        "is false. Do not report only the top-ranked hits."
    )


async def complete_path(
    ref: PromptReference | ResourceTemplateReference,
    argument: CompletionArgument,
    context: CompletionContext | None,
) -> Completion | None:
    """Complete the `path` argument of the status template and the three prompts."""
    if argument.name != "path":
        return None

    is_template = isinstance(ref, ResourceTemplateReference) and ref.uri == _STATUS_TEMPLATE_URI
    is_prompt = isinstance(ref, PromptReference) and ref.name in _PATH_PROMPTS
    if not (is_template or is_prompt):
        return None

    try:
        projects = await _cached_project_paths()
    except ColgrepError:
        return Completion(values=[], has_more=False)

    if is_template:
        # `{+path}` values omit the leading '/' the underlying project paths carry.
        projects = [p.lstrip("/") for p in projects]

    prefix = argument.value
    values = [p for p in projects if p.startswith(prefix)]
    return Completion(values=values, has_more=False)


def register(mcp: MCPServer) -> None:
    """Attach this module's handlers to the server."""
    mcp.prompt(title="Explore: answer a how/why/where question")(explore)
    mcp.prompt(title="Locate: find where a symbol/behaviour lives")(locate)
    mcp.prompt(title="Impact: find what breaks before changing something")(impact)
    mcp.completion()(complete_path)
