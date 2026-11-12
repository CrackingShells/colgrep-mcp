# Findings report from the probe fleet

**Goal**: Publish the harness-probe findings report that turns the measured matrix + R02 into the adjudicated resolution-ladder decision for the next implementation campaign.
**Pre-conditions**:
- [ ] All level-1 and level-2 leaves `done` on the campaign branch (check `dirtree-rdm ls`, not memory): probe instrumentation merged with its verifier sign-off, R02 committed, matrix + raw artifacts present
**Success Gates**:
- ✅ `test -s __reports__/workspace_discovery/01-findings_harness_probe_v0.md`, front matter parses (`type: findings`, `topic: workspace_discovery`, `version: v0`, `prior-version: none`, `key-metric` named, `decision-required` non-empty), and a `## Headline Result` block follows
- ✅ The report's `Resolution Picks` column names one ladder rung per harness, each string-matching a rung id from R01 (dynamic / pin / guarded-cwd / fail+guidance)
- ✅ Every `—` in the matrix is propagated as `—` into the report (no gap is closed in prose)
**References**: [R01 §Proposed State / resolution ladder](../../../../__reports__/workspace_discovery/00-architecture_v0.md) — rung ids the picks must match; [R02](../../../../__reports__/workspace_discovery/01-findings_protocol_survey_v0.md) — channel verdicts the interpretation column cites

## Step 1: Author the harness-probe findings
**Goal**: Write `01-findings_harness_probe_v0.md`; evidence determines every conclusion, dead cells stay dead.
**Implementation Logic**:
Follow `writing-reports` §findings precisely: front matter block first (`key-metric: dynamic_channels_work:` counts harnesses with a live dynamic rung), Headline Result key/value block (`metric/value/unit/prior/direction`), Results Tables (≤20 rows; `harness|run|init_caps|_meta keys|roots verdict|successor|spawn env|Resolution Picks|Notes` condensed from the matrix), Observations four-column table (`Signal|Baseline/Expected|Observed [source: probe_data/harness/raw/<file>]|Interpretation`) whose Baseline column is the R01-predicted ladder — a cell where reality contradicts R01 belongs in `Contradictions & Surprises`, not smoothed over. Add one Mermaid pie or flowchart visual only if slice counts differ (>0 dynamic vs gaps) and carry captions with units where quantitative. `Decision` statement at the end (matching the front-matter `decision-required`): per-call resolution ship scope — which rungs the next campaign wires into `paths.resolve_target_paths`, and the fail+guidance contract for harnesses where all dynamic rungs are `—` (error names `paths` with an absolute directory as the remedy — the pivot the sponsor specified over bare loud-failure). ≤5 Steering Questions tagged `[now]`/`[next run]`/`[later]`; Pointers = links only (matrix, raw JSONL files, R02, R01) even though their filenames embed timestamps. Restate no raw JSON; the tables are the evidence layer, the bars end every claim.
**Deliverables**: `__reports__/workspace_discovery/01-findings_harness_probe_v0.md` (front matter fields `type/topic/date/version/prior-version/key-metric/decision-required`; `## Headline Result`; Results Tables; Observations; optional `## Contradictions & Surprises`; `## Steering Questions`; `## Pointers`; terminal `## Decision` statement with per-harness `Resolution Picks`)
**Consistency Checks**: `grep -q '^type: findings' __reports__/workspace_discovery/01-findings_harness_probe_v0.md && grep -q '^## Headline Result' __reports__/workspace_discovery/01-findings_harness_probe_v0.md` (expected: PASS)
**Commit**: `docs(reports): adjudicate workspace-resolution rungs from probe fleet`
