# workspace_discovery — reports

Reports for the dynamic-workspace-discovery campaign (probe: which per-call
workspace signals each harness delivers, and what the resolution ladder may
trust). Listed by batch round; latest version of each document marked.

| Round | Documents | Status |
|:------|:----------|:-------|
| 00 | [00-architecture_v0.md](00-architecture_v0.md) — resolution ladder, probe dump schema, harness measurement matrix, fail+guidance error model | **latest** |
| 01 | [01-findings_protocol_survey_v0.md](01-findings_protocol_survey_v0.md) (R02, from the protocol_survey leaf, authored by lead per AMS precedent) | **latest** |
| 01 | `01-findings_harness_probe_v0.md` (R03, from the synthesis leaf) | planned |
| 02 | [02-findings_probe_verifier_v0.md](02-findings_probe_verifier_v0.md) — adversarial verifier signed UNSOUND verdict on probe instrumentation (levers + proofs) | **latest** |
| 02 | [02-gap_analysis_calibrated_probe_v0.md](02-gap_analysis_calibrated_probe_v0.md) — amendment gap analysis: probe truth-source gap and proposed `probe_hardening` remedy | **latest** |
| 03 | [03-findings_amendment_review_v0.md](03-findings_amendment_review_v0.md) — formal amendment review verdict (APPROVE, high confidence), persisted for the A1 source column | **latest** |

Status: batches 00–03 landed (architecture, R02 protocol survey, UNSOUND probe verdict, gap analysis, APPROVE amendment review). The amendment's A1 log row and `probe_hardening` node await one granted roadmap-authority call (denied effect this epoch — not retried); `evidence/` stays held pending that fix's adversarial re-signature, per the review's recommendation.
