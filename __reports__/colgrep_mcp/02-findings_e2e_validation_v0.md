# colgrep-mcp End-to-End Validation — Findings (v0)

Date: 2026-09-12

---
type: findings
topic: colgrep_mcp
date: 2026-09-12
version: v0
prior-version: none
key-metric: median warm `search` latency: 759 ms (prior: N/A, delta: N/A)
decision-required: confirm
---

## Headline Result

metric: median warm `search` latency (real `colgrep` 1.6.2, real `pallets/click` clone, through the stdio MCP server)
value: 759
unit: ms
prior: N/A (first end-to-end run)
direction: new

## Results Tables

### Run 1 — warm (corpus already indexed by the lead)

| # | Call | Wall ms | is_error | Hits | Text chars | Truncated | Notes |
|--:|:--|--:|:--|--:|--:|:--|:--|
| 1 | `doctor` | 62 | False | - | 626 | - | |
| 2 | `index_status` | 181 | False | - | 224 | - | |
| 3 | `index_build` | 51 | False | - | 81 | - | up to date |
| 4 | `index_status` | 61 | False | - | 224 | - | |
| 5 | `search` (a) broad semantic, limit=5 | 928 | False | 5 | 1884 | False | |
| 6 | `search` (b) pattern+include, limit=3 | 747 | False | 3 | 1258 | False | |
| 7 | `search` (c) limit=None, no pattern | 767 | False | 15 | 5010 | False | `[LIMIT_DEFAULT_APPLIED]` |
| 8 | `search` (d) pattern+limit=None (exhaustive) | 774 | False | 3 | 1408 | False | |
| 9 | `search` (e) include_code, limit=3 | 757 | False | 3 | 1292 | False | |
| 10 | `search` (f) nonsense query, zero hits | 552 | False | 0 | 159 | False | `[NO_HITS]` |
| 11 | `find_files` limit=5 | 747 | False | 5 | 714 | True | |
| 12 | `expand` top-3 hit_ids of (a), max_lines=40 | 1 | False | 3 | 2234 | - | |
| 13 | `list_indexes` | 51 | False | 161 | 24651 | - | machine-global |
| 14 | resource `colgrep://guide` | 3 | False | - | 7944 | - | |
| 15 | resource `colgrep://status/<corpus>` | 29 | False | - | 642 | - | |
| 16 | prompt `explore` | 2 | False | - | 1017 | - | |
| 17 | `index_clear` (no confirm) | 21 | **True** | - | 208 | - | `[CONFIRMATION_REQUIRED]` (expected) |

Median `search` (a)–(e) wall time: **767 ms** (n=5, sorted: 747, 757, 767, 774, 928).

### Run 2 — cold (`colgrep clear` run immediately before, per R05 D3 guard)

| # | Call | Wall ms | is_error | Hits | Text chars | Truncated | Notes |
|--:|:--|--:|:--|--:|--:|:--|:--|
| 1 | `doctor` | 55 | False | - | 626 | - | |
| 2 | `index_status` | 24 | False | - | 151 | - | not indexed (just cleared) |
| 3 | `index_build` | **16181** | False | - | 116 | - | added: 152, changed/deleted/unchanged: 0 |
| 4 | `index_status` | 176 | False | - | 224 | - | |
| 5 | `search` (a) | 967 | False | 5 | 1884 | False | |
| 6 | `search` (b) | 743 | False | 3 | 1258 | False | |
| 7 | `search` (c) | 766 | False | 15 | 5010 | False | `[LIMIT_DEFAULT_APPLIED]` |
| 8 | `search` (d) | 737 | False | 3 | 1408 | False | |
| 9 | `search` (e) | 825 | False | 3 | 1292 | False | |
| 10 | `search` (f) | 568 | False | 0 | 159 | False | `[NO_HITS]` |
| 11 | `find_files` | 761 | False | 5 | 714 | True | |
| 12 | `expand` | 1 | False | 3 | 2234 | - | |
| 13 | `list_indexes` | 58 | False | 161 | 24650 | - | |
| 14 | resource `colgrep://guide` | 4 | False | - | 7944 | - | |
| 15 | resource `colgrep://status/<corpus>` | 23 | False | - | 642 | - | |
| 16 | prompt `explore` | 2 | False | - | 1017 | - | |
| 17 | `index_clear` (no confirm) | 19 | **True** | - | 208 | - | `[CONFIRMATION_REQUIRED]` (expected) |

`index_build` progress notifications observed: **4** — first=`"indexing <corpus> … 5s"` (heartbeat), last=`"Indexed <corpus> (added: 152, changed: 0, deleted: 0, unchanged: 0)"` (final summary). Median `search` (a)–(e): **766 ms** (n=5, sorted: 737, 743, 766, 825, 967).

### Run 3 — warm again (rebuilt-from-cold index)

| # | Call | Wall ms | is_error | Hits | Text chars | Truncated | Notes |
|--:|:--|--:|:--|--:|--:|:--|:--|
| 1 | `doctor` | 57 | False | - | 626 | - | |
| 2 | `index_status` | 62 | False | - | 224 | - | |
| 3 | `index_build` | 28 | False | - | 81 | - | up to date |
| 4 | `index_status` | 58 | False | - | 224 | - | |
| 5 | `search` (a) | 762 | False | 5 | 1884 | False | |
| 6 | `search` (b) | 753 | False | 3 | 1258 | False | |
| 7 | `search` (c) | 748 | False | 15 | 5010 | False | `[LIMIT_DEFAULT_APPLIED]` |
| 8 | `search` (d) | 739 | False | 3 | 1408 | False | |
| 9 | `search` (e) | 761 | False | 3 | 1292 | False | |
| 10 | `search` (f) | 553 | False | 0 | 159 | False | `[NO_HITS]` |
| 11 | `find_files` | 742 | False | 5 | 714 | True | |
| 12 | `expand` | 1 | False | 3 | 2234 | - | |
| 13 | `list_indexes` | 52 | False | 161 | 24651 | - | |
| 14 | resource `colgrep://guide` | 2 | False | - | 7944 | - | |
| 15 | resource `colgrep://status/<corpus>` | 23 | False | - | 642 | - | |
| 16 | prompt `explore` | 2 | False | - | 1017 | - | |
| 17 | `index_clear` (no confirm) | 20 | **True** | - | 208 | - | `[CONFIRMATION_REQUIRED]` (expected) |

Median `search` (a)–(e): **753 ms** (n=5, sorted: 739, 748, 753, 761, 762).

### Cross-run summary

| Run | Median search (a)-(e) ms | index_build wall ms | index_build notifications | location_verified=false / total hits (a)-(e) | Unexpected errors |
|:--|--:|--:|--:|--:|--:|
| warm-1 | 767 | 51 | 1 | 0/29 | 0 |
| cold | 766 | 16181 | 4 | 0/29 | 0 |
| warm-2 | 753 | 28 | 1 | 0/29 | 0 |
| **combined warm (n=10)** | **759** | — | — | 0/58 | 0 |

`uv run pytest -q -p no:warnings` (against the fake binary, unchanged by this leaf): **170 passed, 1 skipped**.

## Observations

| Signal | Baseline / Expected | Observed [source] | Interpretation |
|:--|:--|:--|:--|
| Warm `search` wall time through the MCP server | R03: raw CLI `--json -k N` search ≈ 0.75–0.78 s (`01-findings_colgrep_behaviour_v0.md` probes 3b/3c/3g/3h/4) | Median 759 ms, range 552-967 ms across all six varieties, n=10 warm calls [`evidence/e2e/warm1.md`, `warm2.md`] | MCP layer (subprocess spawn, JSON parse, `locate_unit`, Pydantic serialization) adds negligible overhead over the raw CLI. R01 Risk 3 (result flood) not triggered at these hit counts (max 5010 text chars, well under the 12 000 budget). |
| Cold `index_build` wall time + progress | R03: raw `init -y` cold ≈ 15.07 s, **no per-file progress**, only a final summary (R05 D2) | 16.18 s wall, **4** progress notifications: 3× 5 s heartbeat + 1 final summary [`evidence/e2e/cold.md`] | D2's heartbeat mitigation for R01 Risk 1 (cold index vs. client timeout) confirmed live against the real binary — a client watching progress would never see a silent multi-second gap. |
| `location_verified` on an untouched fresh corpus | R05 D1: colgrep's own `line`/`end_line` are "frequently wrong" — only ~40% correct across 30 hits in R03 | **0 of 87** hits (29 × 3 runs) across searches (a)-(e) had `location_verified=false` [`evidence/e2e/{warm1,cold,warm2}.md`] | Expected, not contradictory: D1's fix relocates each unit from its own `code` text, which is always correct even when colgrep's *reported* `line`/`end_line` is not — so relocation succeeds whenever the file on disk still matches what was indexed. Risk register item 8 (relocation failing on an edited file) is **not exercised** by this run. |
| `index_clear` refusal wording | R01 §Error model (destructive op without confirmation → `ToolError` naming the flag), updated in parallel by the error-taxonomy leaf to a coded `[CONFIRMATION_REQUIRED] ... Next: ...` shape | Identical coded message reproduced verbatim in all 3 runs: `` [CONFIRMATION_REQUIRED] Refusing to delete the index for <corpus> without confirmation. Next: Call again with `confirm=true`. `` | The coded-error contract (`colgrep_mcp/errors.py`, merged onto `milestone/colgrep_mcp` ahead of this branch) holds end-to-end against the real binary path, including the "no elicitation capability offered by this stdio client" branch of `tools_index.index_clear`. |
| PATH resilience under the real plugin loader (R01 Risk 5) | Plugin launched under a GUI-style client may lack PATH for `uv`/`colgrep` | `claude --plugin-dir <worktree> mcp list` → `plugin:colgrep-mcp:colgrep: .../scripts/launch.sh - ✔ Connected` [this session's terminal output] | `scripts/launch.sh`'s PATH rebuild works end-to-end under the real Claude Code plugin loader, not only under test fixtures. |

## Charts & Visualizations

```
index_build wall time by run (ms; 1 "█" ≈ 500 ms)

warm-1 (up to date)      51 ms |
cold   (full rebuild)  16181 ms |████████████████████████████████  (152 files added)
warm-2 (up to date)      28 ms |
```
Caption: cold rebuild is ~300-580x the warm no-op cost; both warm figures are noise-level (tens of ms).

## Contradictions & Surprises

- The behavioural Claude gate (`claude --plugin-dir ... -p "..."`) failed with `Failed to authenticate: OAuth session expired and could not be refreshed` — exactly the failure mode the roadmap leaf itself pre-flagged ("earlier tonight `claude -p` failed with an OAuth-expired error"). Not a plugin defect; the fallback (`mcp list`, `plugin validate`) is what actually exercises the plugin, and both are green.
- `list_indexes`'s text content (24 650-24 651 chars, 161 machine-global projects) is roughly **2x** the `COLGREP_MCP_TEXT_BUDGET` (12 000) that `search`/`find_files` are held to — by design: `_render_index_list` in `tools_index.py` has no cap at all, and R01's token-budget invariant was written scoped to `search`'s compact listing. Not a contract violation (R05 D9 already calls out `list_indexes` as machine-global), but the gap between "the one tool with an explicit budget" and "the one tool most likely to produce a very large listing on a busy machine" is worth a deliberate decision rather than an accident.
- `find_files(limit=5)` returned `truncated=true` with exactly 5 files shown even though the underlying `search` call surfaced up to 15 hits feeding the de-duplication (`hit_limit = min(limit*3, 300)`) — correct by design, but easy to misread in isolation as "only 5 matches existed."

## Steering Questions

- [now] Is the `mcp list` (✔ Connected) + `claude plugin validate` (✔ Validation passed) fallback sufficient to close this leaf's third Success Gate, given the `claude -p` failure is an environment/OAuth issue outside the plugin's control?
- [next run] Re-run the `claude -p` behavioural gate once a valid OAuth session is available, to get an actual agent transcript citing `file:line` as the roadmap leaf originally intended.
- [next run] Deliberately edit a file between `index_build` and `search` in a future e2e pass to exercise the still-untested `location_verified=false` fallback path (risk register item 8) — this run's fresh, untouched clone never triggers it.
- [later] Decide whether `list_indexes` should get its own text budget or a `path`-scoped/`limit` filter now that a live run confirms its output (161 projects, ~24.6k chars) is unbounded and machine-global by design.
- [later] `release_0_1_0` (sibling leaf) can proceed on schedule — no defect was found on this branch and no `fix(...)` commit was required.

## Pointers

- `server/tests/e2e/run_e2e.py` — the script itself
- `__reports__/colgrep_mcp/evidence/e2e/warm1.md`, `cold.md`, `warm2.md` — full raw output of the three runs (also duplicated as this report's Results Tables)
- `__reports__/colgrep_mcp/00-architecture_v0.md` — §Risks & Mitigations 1, 3, 5
- `__reports__/colgrep_mcp/02-architecture_v1.md` — D1 (locate_unit), D2 (heartbeat), D3 (project folding), D5 (limit default), D7 (index_updated), D9 (list_indexes global scope)
- `__reports__/colgrep_mcp/01-findings_colgrep_behaviour_v0.md` — raw-CLI latency baselines (probes 1, 3b/3c/3g/3h, 4)
- `server/colgrep_mcp/errors.py` — the coded error/hint taxonomy exercised by row 17 of every run
