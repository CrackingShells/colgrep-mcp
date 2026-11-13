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
| 03 | [03-findings_live_probe_v0.md](03-findings_live_probe_v0.md) — live wire probe: both per-call channels measured working, first-call roots race, host rows (Copilot silent; Claude/Codex auth-gated) | **latest** |
| 03 | probe_data/harness/raw/ — ledgers (live_lab-a/b jsonl) + wire transcripts (2026-07-28 / 2025-11-25) | **latest** |

Status: batches 00-03 closed. The analysis deliverable is complete: resolution ladder + probe schema (R00), channel verdicts (R02, Station-1 half-superseded by R03), UNSOUND probe verdict + gap analysis (R02'), amendment APPROVE (R03a), and the live wire probe (R03b) answering the campaign question YES — per-call dynamic resolution works on the wire via request `_meta` vendor keys and per-call roots; host rows measure Copilot silent (the original bug), Claude/Codex gated on transport auth (runs ready). Open for the next cycle: probe_hardening (approved remedy) -> host census replay -> the serving-side resolver fix (roots await/cache race, `_meta` consume, fail+guidance).
