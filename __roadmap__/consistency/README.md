# consistency

## Context
Third campaign of this repository, after `colgrep_mcp` (0.1.0) and `repo_health` (0.1.1). Consumes R01 (`__reports__/consistency/00-architecture_v0.md`), which names the idiom drift left by three parallel implementers and fixes the shared contracts C1–C6; produces a server package with one idiom per concern and two handlers whose I/O is proportional to their output. Client-visible behaviour, tool surface and dependencies are unchanged. Time-boxed: 3 h wall time from 15:57 CEST on 2026-09-12.

## Reference Documents
- [R01 consistency architecture](../../__reports__/consistency/00-architecture_v0.md) — contracts C1–C6, file ownership, risks
- [R05 colgrep_mcp architecture v1](../../__reports__/colgrep_mcp/02-architecture_v1.md) — the behaviour every leaf must preserve (D1–D11, M1–M5)
- [R02 0.1.0 code review](../../__reports__/colgrep_mcp/02-observation_code_review_v0.md) — F1–F14; F2 (cancellation) and F10 (cache race) are touched here

## Goal
One idiom per concern across `server/colgrep_mcp/` — tool definition, path resolution, error translation, client notification, adapter access — and no handler doing I/O the output does not need, with the test suite as the invariance oracle.

## Pre-conditions
- [ ] `cd server && uv run pytest` passes on the campaign branch `claude/mcp-server-consistency-577ab0` (199 passed, 1 skipped after the lead's helper commit `2bb4de2`)
- [ ] R01 committed; the four shared helpers (`server.get_app(ctx=None)`, `paths.resolve_target_paths`, `errors.translate_adapter_errors`, `logging_utils.safe_progress`/`safe_notify_resource_updated`) committed before any leaf is dispatched
- [ ] One worktree per depth-0 leaf created by the lead from the campaign branch at `/Users/hacker/Documents/tmp/claude-worktrees/colgrep_mcp/task-<leaf>`

## Success Gates
- ✅ [run] `cd server && uv run pytest` passes; `uv run ruff check` clean; `uv run cz check --rev-range main..HEAD` passes
- ✅ [behavioral] `Client.list_tools()` / `list_resources()` / `list_prompts()` JSON identical between `main` and the campaign branch (reviewer-verified)
- ✅ [static] `grep -rn` over `server/colgrep_mcp` finds `from_adapter_error(` only in `errors.py`, `Settings.from_env` only in `server.py` and `__main__.py`, `ToolAnnotations(read_only_hint=True` only in `server.py`, no `_standalone_adapter`, no `except Exception:` + `pass`
- ✅ [run] `perf(search)` commit body carries before/after measurements the reviewer reproduced within 2×
- ✅ [static] `__reports__/consistency/` holds the architecture, the review observation and a knowledge-transfer report; `AGENTS.md` has the report-id legend

## Gotchas
- File ownership is disjoint by construction (R01 §Roadmap Recommendation): a leaf edits only its own files; anything else it needs changed is *reported* in the commit body or the final message, never edited.
- Tests are the oracle. A test may be edited only where it imports or monkeypatches a private name the leaf renames; assertions do not change. `tests/test_render.py` must stay byte-identical.
- `Client.list_tools()` JSON is part of the oracle: dump before, dump after, diff empty.
- Never run a real `colgrep` or the e2e driver against this repository or its worktrees (AGENTS.md §Traps). Micro-benchmarks use synthetic files under the scratchpad.
- `perf` commits need measured before/after numbers in the body (CONTRIBUTING); without numbers the type is `refactor`.
- Hard stop: implementers stop and report at 17:30 CEST whatever their state; the lead merges what is green.

## Status
```mermaid
graph TD
    search_tools[Search Tools: One Style, One Renderer, No Wasted Reads]:::done
    index_tools[Index Tools: Shared Resolver, Errors and Notifications]:::done
    context_free_handlers[Resources and Prompts: Share the Lifespan Adapter]:::done
    adapter_hygiene[Adapter and Locks: Per-Spawn Waste]:::done
    integrate[Integrate]:::planned
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `search_tools.md` | 📄 Leaf Task | ✅ Done |
| `index_tools.md` | 📄 Leaf Task | ✅ Done |
| `context_free_handlers.md` | 📄 Leaf Task | ✅ Done |
| `adapter_hygiene.md` | 📄 Leaf Task | ✅ Done |
| `integrate/` | 📁 Directory | ⬜ Planned |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
| `adapter_hygiene.md` | `task/adapter_hygiene` | 1 | lead-implemented; 200 passed; merged 16:12 |
| `context_free_handlers.md` | `task/context_free_handlers` | 2 | Sonnet, ~9 min; validate_call rejects lru_cache wrappers so caching sits one level down; 202 passed; merged 16:19 |
| `index_tools.md` | `task/index_tools` | 2 | Sonnet, ~11 min; list_tools diff empty; doctor now reports roots when env root unset (tested via legacy-mode client); merged 16:20 |
| `search_tools.md` | `task/search_tools` | 3 | Sonnet, ~15 min; list_tools diff empty; find_files 63.4→0.65 ms, expand 6.1→0.03 ms (synthetic, median of 5); merged 16:27 |
