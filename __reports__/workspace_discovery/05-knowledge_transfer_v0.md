# workspace_discovery — Knowledge Transfer (v0)

Date: 2026-11-27

## Executive Summary
- What shipped / changed: the sponsor-folded per-call resolution ladder
  (`explicit paths → request _meta → client roots → COLGREP_MCP_ROOT pin →
  guarded cwd / ROOT_UNRESOLVED guided failure`) landed across three BFS
  levels — hardened dump-only probe (truth-sourced records, never-raise
  boundary, calibration oracle), harness evidence collection, and the
  adjudicating findings report — plus a signed dump-only invariant and four
  lead-integrated verifier fixes (F1–F4).
- Primary outcomes: the silent-wrong-project default is gone (the ladder
  never resolves a root the client did not name, and a fully silent call
  fails with the absolute-`paths` remedy that verifiably works); the fleet
  matrix is honestly all-`—` (`dynamic_channels_work = 0`), scoping the next
  campaign; campaign branch gates green through `cz check --rev-range
  origin/main..HEAD`; landing awaits the maintainer's `gh pr` launch.

## Wins
- File-disjoint leaf ownership (stated in the roadmap Gotchas) + hand-cut
  worktrees from the campaign branch → three level merges, zero conflicts.
- Fail-first discipline held at every landing: `test_first_call_roots_race_regression`
  (`30aad59`), the probe/ladder truth pair (`d759d5e`), and the F1–F4
  close-outs each commit their own first red run in the commit body.
- Custom-endpoint dispatch with explicit slugs from `chatLanguageModels.json`
  (`customendpoint/RiVault/RiVault/Reasoning-Medium`, no effort field) —
  four of four dispatched agents completed; no `400 requested model` fallouts.
- The verifier's margin rule (break-the-guard probes sized to the artefact's
  margin, sizes reported) produced four reproducible findings cheaply, and
  the triage contract (in-roadmap findings fixed, out-of-scope → notice) kept
  the close-out bounded.
- Concurrent evidence + resolution leaves were genuinely file-disjoint at the
  file-graph level; the one shared runtime surface (`_probe_record` needing
  ladder inputs) was caught by the lead's read-back verification and fixed
  before the level closed.

## Pain Points
- The permission model fail-closed the campaign's mutation spine (gate runs,
  merges, host-path tool execution) with epoch-crossing memoization — whole
  dispatch rounds died with zero output in earlier sessions, and `dirtree-rdm`
  bookkeeping is still blocked (status tables stale at time of writing).
- A `revert(server)` subject (not in the cz vocabulary) survived two rebases
  from an earlier round and was caught only by the campaign-range `cz check`.
- The harness rows are all `—`: a `doctor`-only trigger is never invoked by
  `claude -p` / `codex exec` (auth-gated per R03b), so the matrix measures
  sample absence, not channel absence.
- One brief mislabel ("git-ignored leftovers") sent the evidence implementer
  to report committed citation evidence (`wire-*`, `live_lab-*`) as candidate
  debris — caught at merge read-back and corrected as a boundary note.
- Cross-leaf call-graph coupling (`resolve_target_paths` → probe hook) between
  two simultaneously dispatched leaves produced the `d759d5e` divergence.

## Root Causes
- No stored allow rules for the DAG's critical commands → unattended roadmap
  runs cannot complete their own merge/gate spine.
- Roadmap authoring tooling (`dirtree-rdm`) ships as a host-path plugin script
  the workspace cannot execute under a workspace-scoped permission policy.
- File-disjoint ownership does not cover call-graph coupling: the probe hook
  and the ladder share one runtime path, so both leaves needed the same helper
  (`default_root` with `meta_root`) wired through `_probe_record` — that helper
  should have been a pre-dispatch lead commit (campaign-lead rule 3).

## Next-cycle Changes
1. Stamp allow rules for the recurring gate/merge spine (`git` merge/rebase/
   commit under `.worktrees/`, `uv run pytest|ruff|cz`) so unattended DAG runs
   finish; leave destructive effects (worktree remove) prompting.
2. Move `dirtree-rdm` into the repo (`dev/skills/managing-roadmaps/scripts/`)
   so bookkeeping never depends on host-path execution; run status writes at
   every level close.
3. Dispatch policy: when two leaves share a call-graph path, sequence them or
   pre-commit the shared helper — applies to any future `paths.py` + probe
   pairing.
4. Evidence leaves must name their auth precondition in Pre-conditions and use
   a trigger the target harness reliably invokes; `doctor`-only produced
   honest but static evidence.
5. Run `cz check --rev-range campaign-base..HEAD` at level START as well as
   close — legacy subjects should burn at rebase time, not at the end.
6. Carry the close-out pairing forward: one commit per verifier finding,
   regression test + fail-first quote + fix together (see `3f35c65`, `1e9d845`,
   `544d308`).

## Artifacts to Preserve
- [04-findings_dump_only_signature_v0.md](04-findings_dump_only_signature_v0.md) —
  the four listing digests the dump-only invariant is signed against.
- [01-findings_harness_probe_v0.md](01-findings_harness_probe_v0.md) — fleet
  adjudication and the terminal `## Decision` scoping the next campaign.
- [probe_data/harness/matrix.md](probe_data/harness/matrix.md) and the raw gap
  records —   the honest-`—` matrix and its named gaps.
- The F1–F4 reproducers, now pinned as regression tests in
  [test_paths_resolution.py](../../server/tests/test_paths_resolution.py):
  `test_named_remedy_is_itself_a_working_escape`,
  `test_pathless_file_uri_root_never_scopes_the_filesystem`,
  `test_classify_needs_usable_items_for_declared`,
  `test_concurrent_first_calls_both_reassure_before_settling`.
- The roots reassurance state machine (`paths.py`: `_roots_settled`,
  `_FIRST_EMPTY_WAITERS`) — a subtle concurrency contract: the budget belongs
  to the unsettled state, and outcomes must never be decided from a stale
  provisional empty.

## Open Questions
- Name the `roots/list` successor (R02 Station 1 opener) — rung 2 stays
  at-best-static until then (carried from the findings Steering Questions).
- Re-probe the fleet from authenticated sessions: is any fleet harness
  actually stamping `_meta` or answering `roots/list` per call?
- Should the reassurance wait bound (0.1 s) be configurable, and is 0.1 s the
  right steady-state cost when a first call and a slow harness coincide?
- The campaign branch's `gh pr` landing is pending; CI's Windows leg is the
  first to run this ladder's path-handling (`url2pathname` roots, F2 guard) —
  read its verdict before cutting a release.
