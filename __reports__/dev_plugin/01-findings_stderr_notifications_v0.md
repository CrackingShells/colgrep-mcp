# Stderr Notifications — Findings (v0)

Date: 2026-09-12

---
type: findings
topic: dev_plugin
date: 2026-09-12
version: v0
prior-version: none
key-metric: notifications/message frames per search (synthetic cold-build chatter): 1 (prior: 3, delta: -2)
decision-required: none
---

## Headline Result

metric: notifications/message frames per `search` call, synthetic 3-line cold-build stderr
value: 1
unit: frames
prior: 3
direction: down

## Results Tables

### Frames and bytes per `search` call (legacy-mode `Client`, `logging_callback`)

| Scenario | Frames (before) | Bytes (before) | Frames (after) | Bytes (after) |
|---|---|---|---|---|
| Real `fake_colgrep.py`, plain `search` (no stderr emitted) | 0 | 0 | 0 | 0 |
| Synthetic 3-line cold-build chatter (R05 D2 shape) | 3 | 127 | 1 | 77 |

### `find_files` conversion micro-benchmark (300 synthetic raw hits / 100 files, median of 5)

| Path | Time (ms) |
|---|---|
| Old: `hit_from_raw` per hit, then fold to `FileHit` | 0.684–0.693 |
| New: direct `FileHit` fold (`_file_hits_from_raw`) | 0.124–0.126 |

## Observations

| Signal | Baseline / Expected | Observed | Interpretation |
|---|---|---|---|
| `fake_colgrep.py`'s `search` subcommand stderr | Expected to emit the same cold-build chatter `init` does (R05 D2), per the leaf's premise | Zero stderr lines from `search` in every scenario [source: `tests/fake_colgrep.py`, dispatch table has no `search` branch writing to stderr] | Fixture gap: the fake only reproduces colgrep's cold-build banner for `init`, never for `search`'s own auto-index. `search`'s notification behaviour could not be measured against the real fixture; a synthetic stand-in (`_StderrInjectingAdapter` in the test file, substituting for `get_adapter`) was used instead to reproduce the shape a real cold `search` would emit. |
| `find_files` never calling `hit_from_raw` | 0 calls expected, R01 §C6 | 0 calls, pinned by `test_find_files_never_builds_search_hits` [source: `server/tests/test_tools_search.py`] | Matches the contract; the old code called it once per raw hit (up to 300) even with `locate=False`. |
| `search` notification count with real chatter | ≤1 per call, 0 when index already current | 1 frame when `index_updated` (3-line synthetic chatter), 0 frames with none [source: `test_search_sends_at_most_one_log_notification`, `test_search_sends_zero_log_notifications_when_index_already_current`] | Matches the R01 §C6 decision: one summary notification replaces one-per-line forwarding. |

## Contradictions & Surprises
- The leaf's premise ("the fake, which emits its index-update chatter on stderr" during `search`) does not hold: `fake_colgrep.py`'s `search` subcommand never writes to stderr — only `init` does. Since `fake_colgrep.py` is unowned this cycle, the notification-count measurement and the two new pinning tests were built against a synthetic `get_adapter` stand-in (`_StderrInjectingAdapter`) instead of the real subprocess, reproducing the 3-line cold-build shape from `evidence/colgrep/01_cold_init.stderr.txt` (R05 D2). The measured saving against the *unmodified* fixture is 0→0 frames (nothing to save, because nothing is emitted); the measured saving against a faithful reproduction of what real colgrep's `search` auto-index actually emits is 3→1 frames, 127→77 bytes. The `perf(search)` commit type and numbers in this report follow the synthetic measurement, since it is the one that reflects the change's actual effect; the 0→0 real-fixture number is recorded here rather than silently dropped.

## Steering Questions
- [now] Should `fake_colgrep.py` gain a knob (e.g. `FAKE_COLGREP_SEARCH_COLD` or reusing the existing cold-build lines) so `search`'s own auto-index chatter is reproducible without a synthetic adapter substitution? Out of this leaf's ownership; flagged for whoever next owns `tests/fake_colgrep.py`.
- [next run] `find_files` now shares `_run_adapter_search` with `search`, so it also gets the one-summary-notification behaviour (previously it inherited the same per-line forwarding `search` did, since both went through the same `_do_search`). Worth confirming this is desired — the leaf's C6 contract names only `search`, but `find_files`'s prior behaviour was identical, so this is a consistency improvement rather than a new divergence.
- [later] The double `resolve()` of `unit.file` open question (KT-C) was not touched this leaf; `_resolve_hit_file`/`_file_hits_from_raw` still call it at most once per hit as before.

## Pointers
- `server/colgrep_mcp/tools_search.py` — `_run_adapter_search`, `_file_hits_from_raw`, `_do_search`.
- `server/tests/test_tools_search.py` — `test_find_files_never_builds_search_hits`, `test_search_sends_at_most_one_log_notification`, `test_search_sends_zero_log_notifications_when_index_already_current`.
- `__reports__/dev_plugin/00-architecture_v0.md` §C6, §C8.
- `server/tests/fake_colgrep.py` (fixture gap noted above; not edited).
