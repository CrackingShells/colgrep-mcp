# list_indexes Text Budget

**Goal**: `list_indexes` renders its machine-global text through the one budgeted renderer so it never exceeds `settings.text_budget`, while `structured_content` stays complete.
**Pre-conditions**:
- [ ] Working in worktree `/Users/hacker/Documents/tmp/claude-worktrees/colgrep_mcp/task-list_indexes_budget` on branch `task/list_indexes_budget` (created by the lead from the campaign branch); this file exists there — if it does not, stop and report
- [ ] R01 §C7 and §C8 read; `cd server && uv run pytest` passes on the branch
**Success Gates**:
- ✅ [behavioral] `Client.list_tools()` JSON dumped before and after is identical (no schema, argument or description change)
- ✅ [run] a test with 400 fake indexes asserts the text is ≤ `text_budget` characters, ends with a continuation note naming the remaining count, and `structured_content["indexes"]` has all 400; the test fails against the pre-change code (say so in the commit body)
- ✅ [run] `cd server && uv run pytest && uv run ruff check && uv run ruff format --check` green
**References**: [R01 §C7 list_indexes budget, §C8 oracles](../../__reports__/dev_plugin/00-architecture_v0.md) — the contract and the oracle; [R05 token-budget invariant](../../__reports__/colgrep_mcp/02-architecture_v1.md) — the invariant every other renderer already honours

## Step 1: Render list_indexes through the budgeted renderer
**Goal**: The text an agent reads is capped like every other tool's, with the full list one `structured_content` away.
**Implementation Logic**:
Dump `Client.list_tools()` into the scratchpad first. In `tools_index.py`, make `_render_index_list(result, budget)` call `tools_search._render_budgeted(header, blocks, more_note, [], budget)` — the one budgeted renderer (R01 consistency §C5) — with header `"<n> indexed projects on this machine"` (keep the exact empty-list sentence unchanged), one block per index in the current `project  model=…  units=…  searches=…` shape, and `more_note = lambda k: f"[{k} more indexes in structured_content]"`. `list_indexes` passes `get_settings(ctx).text_budget` and, when capped, sends one `safe_log(ctx, "warning", ...)` like `find_files` does. Do not add fields to `IndexList`. Test: monkeypatch the adapter's `stats()` to return 400 `IndexInfo`s with long paths; assert length and completeness as the gate says; also assert the single-index rendering is byte-identical to before (keep the existing `test_list_indexes_count` green). Run the new test against the old code first. Re-dump `list_tools()`; `diff` empty.
**Deliverables**: `server/colgrep_mcp/tools_index.py` (`_render_index_list(result, budget)` through `_render_budgeted`; `list_indexes` passes the budget and logs when capped), `server/tests/test_tools_index.py` (`test_list_indexes_text_is_budgeted_and_structured_content_is_complete`)
**Consistency Checks**: `cd server && uv run pytest -q && uv run ruff check && uv run ruff format --check` (expected: PASS)
**Commit**: `fix(index): cap list_indexes text at the text budget like every other renderer`
