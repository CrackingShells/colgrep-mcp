# Amendment Review — Findings (v0)

Date: 2026-11-13

---
type: findings
topic: workspace_discovery
date: 2026-11-13
version: v0
prior-version: none
key-metric: amendment_decision: APPROVE (confidence: high) (prior: N/A, delta: N/A)
decision-required: confirm
---

## Headline Result

metric: amendment_decision
value: APPROVE
unit: reviewer verdict on the `probe_hardening` amendment (confidence: high)
prior: N/A
direction: new

## Results Tables

### Review columns (amendment-review-bound, dispatch turn 0, 12s)

| Column | Reviewer verdict | Independent source check |
|:-------|:-----------------|:-------------------------|
| Validity of gap as stated | Real | Confirmed against `probe.py`, `test_probe.py`, `probe_workspace.py`: three-plus silent-falsification / raise-escape paths on exactly the `tool`, `init_capabilities`, `roots_list` columns the evidence matrix must trust |
| Root-cause vs impact consistency | Consistent | The missing-calibration-witness root cause flows directly into the blind-oracle finding and the unfalsifiable-matrix impact; no overreach identified |
| Proposed solution fit vs never-raise law | Strong fit | Hardening steps make `record` total for arbitrary inputs (closing the confirmed `TypeError` escape past `paths.py:113`) inside the module's own "must never raise" law; consistent with maintainer-policy §one-idiom-per-concern and §hardware-first |
| Recommendations practical vs prior contracts | Consistent | Holding level 2 until adversarial re-signature matches the roadmap Gotcha; retaining `forge_record`/`diff_record` under `probe.py` avoids drift, per gap-analysis recommendation 3 |
| Gap-analysis fidelity to cited findings | Faithful | Each cited lever (1b, 2, 2b, 3, 5, 6) reproduces the findings table; all six independently re-verified line-of-source (stub hardcodes, brittle `_probe_tool_name` frame scan, `capture_pure` outside the `try` block, env-var-only assertion, `snap["ts"]` KeyError on gap records, `roots_static` collapsing error into empty) |

## Observations

| Signal | Baseline / Expected | Observed [source] | Interpretation |
|:-------|:--------------------|:------------------|:----------------|
| Formal review (amendments.md step 4) evidence must live in the reports store | Same rule that forced the findings into 02- files before the amendment dispatch | Reviewer verdict materialized here, not chat-only [source: run rules — chat is not association-visible] | The amendment's A1 source column can now legitimately widen from just the gap analysis to gap analysis + this verdict |
| Branch status updates (evidence dispatch hold) in pipeline | Already-rowed for protocol_survey gotcha | Blocked effect surface this epoch (denied roadmap batch) [source: runtime permission log] | Vicious: cannot hand-place `probe_hardening` node OR mark any leaf status until grant arrives |

## Steering Questions

- [now] Grant the roadmap batch authority once: `dirtree-rdm add probe_hardening.md` + one `dirtree-rdm update protocol_survey done` — one clean effect set, no retries bundled with unrelated commands (the bundling caused this epoch's denial).
- [next run] Implement `probe_hardening` at level 1 per the drafted steps, re-verify its calibration oracle failing on the shipped faulty state, then a fresh adversarial signer replaces the UNSOUND verdict before `evidence/` opens.

## Pointers

- ../../__reports__/workspace_discovery/02-gap_analysis_calibrated_probe_v0.md — the proposal this verdict approves
- ../../__reports__/workspace_discovery/02-findings_probe_verifier_v0.md — the evidence base
- ../../__roadmap__/workspace_discovery/README.md — target of the pending amendment log update
