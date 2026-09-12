# Reports — consistency

## Round 00
- `00-architecture_v0.md` — architecture analysis: the idiom drift across `server/colgrep_mcp/` (tool style, error translation, path resolution, renderers, standalone adapters, notification guards), contracts C1–C6, file ownership per leaf, risks

## Round 01
- `01-observation_review_v0.md` — read-only review of the merged depth-0 result: schema invariance, leftover idioms, cancellation/concurrency fixes (F1/F2/F6/F10) all confirmed intact, `find_files` byte-identical, both perf claims reproduce within 2×, `resolve_target_paths` roots-call counts correct; one new confirmed risk (OV1: the module-global `_app` handle in `server.py` is corrupted by two overlapping — not sequential — lifespans in one process) (latest)

## Round 02
- `02-knowledge_transfer_v0.md` — retrospective: what converged, measured wins (reviewer-reproduced), pain points (roadmap grammar, `merge -F -`, `validate_call` vs `functools.cache`, a regression test that passed on the broken code), next-cycle changes and follow-ups (latest)

## Status
Campaign opened and closed 2026-09-12 (15:57 → 16:48 CEST, ≈50 min of a 3 h box). Lead (Fable) committed the shared helpers (C1–C4), the roadmap and two glue commits, took the adapter leaf, and integrated six Sonnet branches (three implementers at depth 0, one implementer and one reviewer at depth 1) with rebase then `--no-ff`. The review's one confirmed risk (OV1) is fixed on the branch. All nodes of `__roadmap__/consistency/` are done. PR #3's first CI run exposed a Windows client-root bug the new doctor test made reachable (fixed on the branch, see the retrospective); 208 tests pass. Landed on `main` as PR #3 (merged 17:43 CEST) and released as v0.1.2 through `cz bump`, the same afternoon.
