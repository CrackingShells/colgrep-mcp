# Harden probe: truth-source, never-raise, calibration oracle

**Goal**: Make the workspace-signal probe trustworthy by construction: truth-sourced record columns, a total never-raise boundary, and a calibration oracle that fails when the probe lies.
**Pre-conditions**:
- [x] Gap analysis + UNSOUND verdict + APPROVE review landed (02-gap_analysis_calibrated_probe_v0.md, 02-findings_probe_verifier_v0.md, 03-findings_amendment_review_v0.md)
- [ ] Branch cut from the campaign branch with the reports visible (worktrees see only committed files)
**Success Gates**:
- ✅ `cd server && uv run pytest -q` green; `test_no_probe_side_effects` fails against the shipped faulty state (commit body names how) and passes here
- ✅ A sabotaged probe (records fabricated `init_capabilities`) fails the calibration oracle test: `diff_record` must whistle on a stub-authored record verbatim
- ✅ `record()` is demonstrably total: no input (`ctx=None`, non-serializable snapshot values, unwritable probe dir) raises past the resolve call site
**References**: [R02' §Evidence](../../__reports__/workspace_discovery/02-gap_analysis_calibrated_probe_v0.md) — the four defect lines each step repairs; [R02 §Lever table](../../__reports__/workspace_discovery/02-findings_probe_verifier_v0.md) — exploit chains the fixes must retire

## Step 1: Truth-source the record columns
**Goal**: Every ledger column reflects what was measured, never what the probe can guess.
**Implementation Logic**:
Re-land `server/colgrep_mcp/probe.py` with the revert-backed facility but two repairs. (1) `tool` attribution: accept the tool name explicitly at the hook site in `paths.resolve_target_paths` (or scan frames skipping module-internal names) — the record must name the actual tool, not `"record"`. (2) `roots_list`: three values `declared` / `empty` / `error` — `error` when the round-trip raised or the back-channel is absent, `empty` only when a client actually answered with zero roots. Both columns verified against the verifier's lever-1/6 chains.
**Deliverables**: `server/colgrep_mcp/probe.py` (exports `capture_pure`, `record`, `PROBE_ENV`, `FORGED_SAMPLE`); `server/colgrep_mcp/paths.py` (hook passes `tool` and the distinct roots outcome); `server/tests/test_probe.py` (`test_tool_column_names_the_actual_tool`, `test_roots_error_distinct_from_empty`)
**Consistency Checks**: `grep -q 'probe_hardening' __reports__/workspace_discovery/02-gap_analysis_calibrated_probe_v0.md` (expected: PASS)
**Commit**: `fix(server): make probe record columns reflect measured truth`

## Step 2: Make record() total — no raise escapes to the resolve path
**Goal**: The never-raise law becomes a property, not a docstring claim.
**Implementation Logic**:
Wrap the whole body after the env sentinel in one `try/except Exception` (OSError **and** TypeError from `capture_pure` serialization of hostile values), `safe_log` on failure. Regression: a snapshot value that is not JSON-serializable must produce either a coerced record or a swallowed failure — the `tools/call` must succeed either way (this is lever 2b's kill). Prefer coercion in `capture_pure` (`default=str`) over silent loss so the record remains a witness.
**Deliverables**: `server/colgrep_mcp/probe.py` (total `record`, coerced `capture_pure`); `server/tests/test_probe.py` (`test_record_never_raises_on_hostile_snapshot`, `test_tool_call_survives_probe_rename`)
**Consistency Checks**: `cd server && uv run pytest tests/test_probe.py -q` (expected: PASS)
**Commit**: `fix(server): make the probe record path survive hostile snapshots`

## Step 3: Calibration oracle — forge_record / diff_record
**Goal**: Ship the witness the gap analysis prescribes: the test harness can catch a probe that lies.
**Implementation Logic**:
In `probe.py`: `forge_record(**overrides) -> dict` builds a ground-truth record from an explicit snapshot (no frame reading, no env reading), and `diff_record(expected, actual) -> list[str]` returns the field-level disagreements. `test_probe.py` adds `test_calibration_whistles_on_fabrication`: feed a record with fabricated `init_capabilities` and assert `diff_record` is non-empty; feed the true record and assert empty. The old `test_no_probe_side_effects` is rewritten to read the actual ledger path (`colgrep_probe.jsonl`, not the dead filenames the old test asserted) and compare `capture_pure` round-trip against `forge_record` output. Record in the step-1/2 commit bodies that the OLD test never failed on the faulty state (it was blind) — the new ones must initially fail against the states in `02-findings_probe_verifier_v0.md` lever 3 to earn the name.
**Deliverables**: `server/colgrep_mcp/probe.py` (exports `forge_record`, `diff_record`); `server/tests/test_probe.py` (`test_calibration_whistles_on_fabrication`, `test_no_probe_side_effects` rewritten against the real ledger path)
**Consistency Checks**: `grep -q 'forge_record\|diff_record' __reports__/workspace_discovery/02-gap_analysis_calibrated_probe_v0.md` (expected: PASS)
**Commit**: `test(tests): add the probe calibration oracle and retire the blind ledger test`

## Step 4: Driver provenance and gap-record tolerance
**Goal**: Stub-written rows are labelled as such, and the driver's own gap signalling stops crashing its validator.
**Implementation Logic**:
`server/tests/e2e/probe_workspace.py`: every stub-written record adds `"provenance": "stub"` (server-written rows carry `"provenance": "server"` or omit); `_validate_record` tolerates `{"error": ...}` gap rows (they parse to `gap_record` verdicts instead of KeyError-ing on `snap["ts"]`); the rotation writer keeps whole raw dirs in `__reports__/workspace_discovery/probe_data/`. A validator call with a gap row must return a named gap, never raise.
**Deliverables**: `server/tests/e2e/probe_workspace.py` (stub records stamped `provenance: "stub"`; gap-tolerant `validate`); `server/tests/test_probe.py` (`test_gap_records_validate_as_gaps`, `test_stub_records_carry_provenance`)
**Consistency Checks**: `cd server && uv run pytest tests/test_probe.py -q` (expected: PASS)
**Commit**: `fix(tests): stamp stub provenance and let gap rows round-trip the validator`
