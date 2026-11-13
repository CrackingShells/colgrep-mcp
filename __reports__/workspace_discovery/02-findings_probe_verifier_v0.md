# Probe verifier — Findings (v0)

Date: 2026-11-13

---
type: findings
topic: workspace_discovery
date: 2026-11-13
version: v0
prior-version: none
key-metric: dump_only_law: REFUSED (UNSOUND) (prior: N/A, delta: N/A)
decision-required: intervene
---

## Headline Result

metric: dump_only_law
value: REFUSED (UNSOUND)
unit: adversarial signer verdict
prior: N/A
direction: new

## Results Tables

### Lever attack outcomes (verifier: probe-verifier-v3, dispatched at escalated tier)

| Lever | Outcome | Proof |
|:------|:--------|:------|
| 1. Silent falsification (record fabrication) | exploitable | `probe.py` `_probe_tool_name()` frame scan always resolves to `record` itself, so every ledger line claims `"tool": "record"`; `probe.py:88-92` maps an exceptioning `client_roots` (per `paths.py:60-61` `except` call) to `{"static": "empty"}` — an emptiness the harness never sent |
| 1b. Doctor-stub impersonation | exploitable | `probe_workspace.py:51-70` stub synthesizes full R01 records with literals `"init_capabilities": None`, `"request_meta": None`, `"roots_list": {"static":"empty"}` on every invocation; `validate()` (`:158-183`) checks key presence only and passes them |
| 1c. getattr fallbacks (`init_caps`/`req_meta`) | inconclusive (execution-blocked) | statically: absent values recorded as `None`, never synthesized; live probe runs and `context7`-routed source inspection were both permission-denied at the dispatcher end |
| 2. Env-value escapes (`=""`, `=0`, `=/dev/null`, parent-is-file) | not exploitable (with debris) | `=""` inert at `probe.py:84`; `/dev/null` and parent-is-file raise `FileExistsError`/`NotADirectoryError` ⊂ `OSError`, caught (`:133-135` buffer) → `safe_log`, no debris; bare `=0` writes `./0/colgrep_probe.jsonl` in server cwd — documented-location debris, not a law break |
| 2b. Raise past the inertness law | exploitable (reachability inconclusive) | `capture_pure(record_obj)` (`probe.py:132`) sits outside the `try`/`except OSError`; a non-`model_dump`, non-serializable snapshot value raises `TypeError` through `_probe_record` → `paths.py:113`, breaking the tool call the module docstring promises never to break |
| 2c. Probe-on/off resolution difference | not exploitable | records write only under `$COLGREP_MCP_PROBE/` (`:133-135`), `default_root` is pure and inputs untouched — byte-identical outcomes except when 2b fires |
| 3. Regression honesty (`test_no_probe_side_effects`) | exploitable (blind oracle) | test deletes `COLGREP_MCP_PROBE` first (`test_probe.py:229`), so `record()` early-returns nothing observable; its sole post-call assertion re-reads the environment variable (`:247-251`), never a ledger; fs assertions check filenames the implementation never writes (`probe.jsonl`, `~/colgrep_probe.jsonl` vs the real `colgrep_probe.jsonl`) rather than content. A probe fabricating `init_capabilities` passes the whole test. |

### Driver liveness audit

| Surface | Outcome | Proof |
|:--------|:--------|:------|
| Real-colgrep leak | PASS (no violation) | the driver's only `subprocess.run` is `[harness_exe, "-p", TRIGGER_PROMPT]` (`probe_workspace.py:110`); `colgrep` is reached solely as the stub it writes (`:81-94`); no test writes `~/Library/Application Support/colgrep` or `~/.local/share/colgrep` (those strings are fixture text only) |

## Observations

| Signal | Baseline / Expected | Observed [source] | Interpretation |
|:-------|:--------------------|:------------------|:----------------|
| Ledger can prove its own provenance beyond stub-written copies | R01 probe dump schema contract (report `00-architecture_v0.md`) | Stub-written records pass `validate()` unchanged [source: verifier lever 1b, repro static] | The evidence plan cannot trust any matrix cell whose `init_capabilities`/`roots_list` value equals the stub's hardcode |
| Always-non-raising claim in `probe.py` docstring | Leaf step 1 law ("best-effort" never raises) | `capture_pure` outside the try boundary, `TypeError` reachable through resolve path [source: verifier lever 2b] | Even one non-serializable snapshot breaks tool calls — the leaf's own headline invariant fail, not cosmetic |
| Root cell for a failed round-trip | The word `empty` should mean "genuinely nothing sent", distinct from "we couldn't ask" | Both collapse to `{"static": "empty"}` [source: verifier closed-workflow finding 6] | A matrix whose "race" column means "the call errored" cannot be scores for the campaign's Station 1 decision — this invisibly biases rung picks |
| Fleet validation path | `validate()` reports gap records as gaps, not crashes | Gap records crash `_validate_record` (key `snap["ts"]`) [source: verifier closed-workflow finding 5] | The driver literally cannot use its own gap signalling; needs tolerance before R03 uses it |

## Charts & Visualizations

```mermaid
graph TD
    stub["_STUB_SCRIPT writes R01-shaped record"] --> doctor["doctor tool call"]
    doctor -.->|"bypasses resolve_target_paths"| nonemissive["no server record written"]
    nonemissive →|stub lines only| ledger["colgrep_probe.jsonl"]
    validate["validate() checks keys only"] -->|passes| ledger
    matrix["R03 matrix cells read ledger"] -->|believes| falsified["falsified init_capabilities / roots_list"]
```

Caption: verifier's exploitation chain (lever 1b + lever 3); every matrix cell values a record the harness never sent, and the gate designed to catch it never read the ledger.

## Contradictions & Surprises

- The probe module's *architecture doc* (R01 §Contracts & Invariants) already stated the dump-only invariant and the "raw values only" law — the defect is not a missing contract but a missing calibration witness (see the independent Gap Analysis `02-gap_analysis_calibrated_probe_v0.md` root cause).

## Steering Questions

- [now] Accept the gap analysis: probe must ship a truth-source oracle (`forge_record`/`diff_record`) and the stub must mark record provenance before any harness run is trusted.
- [now] Decide whether the driver's gap-record path or the provenance-marking change moves first (ordering for the fix leaf).
- [next run] A fresh verifier (protocol-adjusted ask of the same campaign-lead attack) must sign the repaired probe before `evidence/` dispatch opens.
- [later] Generalize: any collected evidence tool in this repo defaults to shipping its own calibration fixture ("tests can run is not tests can prove") — codify in `maintainer-policy` once (a future campaign).

## Pointers

- ../../__reports__/workspace_discovery/02-gap_analysis_calibrated_probe_v0.md — gap analysis built on these findings
- ../../__roadmap__/workspace_discovery/README.md — campaign debt note this supersedes
- ../../server/colgrep_mcp/probe.py — defect region 1, 1c, 2b, 6
- ../../server/tests/test_probe.py — defect region 3
- ../../server/tests/e2e/probe_workspace.py — defect regions 1b, 5
