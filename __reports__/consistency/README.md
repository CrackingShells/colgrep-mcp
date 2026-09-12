# Reports — consistency

## Round 00
- `00-architecture_v0.md` — architecture analysis: the idiom drift across `server/colgrep_mcp/` (tool style, error translation, path resolution, renderers, standalone adapters, notification guards), contracts C1–C6, file ownership per leaf, risks

## Round 01
- `01-observation_review_v0.md` — read-only review of the merged depth-0 result: schema invariance, leftover idioms, cancellation/concurrency fixes (F1/F2/F6/F10) all confirmed intact, `find_files` byte-identical, both perf claims reproduce within 2×, `resolve_target_paths` roots-call counts correct; one new confirmed risk (OV1: the module-global `_app` handle in `server.py` is corrupted by two overlapping — not sequential — lifespans in one process) (latest)

## Status
Campaign opened 2026-09-12 15:57 CEST, boxed to 3 h. Lead (Fable) committed the shared helpers (C1–C4) and the roadmap `__roadmap__/consistency/`, then dispatched three Sonnet implementers on file-disjoint leaves and took the adapter leaf itself. Round 01 (review observation) is done; `task/docstrings` (`integrate/docstrings.md`) is in progress on a sibling branch, not yet merged. The knowledge-transfer report follows both.
