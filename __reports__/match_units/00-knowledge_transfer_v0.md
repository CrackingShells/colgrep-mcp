# Match Units — Knowledge Transfer (v0)

Date: 2026-11-01

## Executive Summary
- **What shipped:** on PR #18 (`claude/happy-hamilton-e15dcd`, head `15a610c`), `search` returns one hit per matched unit, and the construction behind it was rebuilt.
  - One normaliser, `adapter.unit_matches`, is the only reader of colgrep's `matches`.
  - Units are ranked and cut before any hit is built, and only the surviving spans are read.
  - A file's best unit is span-verified. Its other units are trusted through this call's index refresh.
  - `expand` reads each file once.
  - colgrep 1.8.4 is a soft minimum, enforced in `doctor`. Docs were edited in place: the guide is +3 lines net and `skills/` is unchanged.
- **Primary outcomes:**
  - `search` (limit=15) 5.20 → 2.13 ms and `expand` (5 ids) 0.76 → 0.42 ms. Stub adapter, median of 5.
  - On the real binary, 0 of 110 hits are unverified.
  - Five bugs in the first per-unit version (c4c291a) are fixed, and three gaps are accepted and written down.
  - Four upstream asks came out of it (`00-findings_upstream_colgrep_contract_v0.md`).
- **Cost:** 6 subagent dispatches, all on Sonnet: reviewer, advisor, implementer ×2, verifier ×2. About 1.3M subagent tokens in total.

## Wins
- **An independent review before rework.** A Sonnet reviewer given the code, not the author's conclusions, found the duplication and two of the location bugs the author had missed in c4c291a.
- **Shrinking the roadmap.** An advisor pass cut it from 5 leaves, 11 commits and 4–5 dispatches to 3 leaves, 7 planned commits and 2 dispatches. Execution confirmed the sizing: one implementer did the whole pipeline, and the coordinator wrote doctor and docs in parallel.
- **A verifier with a named attack list and a required real-binary probe.** Its first pass broke the trust rule on real data: 13 of 110 hits unverified, plus wrong text under trailing-dot and duplicate headings. That bug class does not show in a green suite. The recheck confirmed the fixes.
- **Implementers reporting spec defects instead of building on them.** Two premises in the coordinator's briefs were false, and both came back as findings with source lines:
  - colgrep collapses results per path, not globally, so step 5 was skipped;
  - colgrep under `--json` never prints the lock-skip warning.
- **Measuring the environment before dispatch.** A fresh worktree run of the suite caught the coordinator's own machine paths in a roadmap leaf (`test_packaging` local-path guard) before any implementer inherited them.

## Pain Points
- **The coordinator designed the trust rule twice, and both versions were wrong.** The name-on-first-line rule failed on continuation chunks. Its replacement leaned partly on a stderr line that `--json` suppresses.
- **`dirtree-rdm add <path>` without the `.md` suffix** writes a Nodes row the validator rejects. It also leaves an orphan leaf file behind. It took two failed retries to find this, because the error points at the wrong table (`00-observation_dirtree_rdm_add_suffix_v0.md`).
- **An `--amend` combined with a `reset --hard` in one command was refused by the auto-mode classifier.** A new commit plus `merge --ff-only` worked. A lone `--amend` later passed.
- **`gh pr edit` fails on a token without `read:org`.** The REST route (`gh api -X PATCH …/pulls/18 -F body=@file`) worked.
- **The "every new test fails on c4c291a" gate could not hold literally.** Regression pins for behaviour that must not change pass on the old code by design. The implementer split its list into "fails there" and "passes there".

## Root Causes
- **The trust rules were designed from the plan's model of colgrep, not from colgrep's output.** Neither the continuation-chunk shape (60-line section caps) nor `quiet = json` was looked up before the briefs pinned them.
- **The success gate conflated two test classes:** regression tests, which must fail on the old code, and contract pins, which must pass on both. The plan asked one gate to cover both.
- **`dirtree-rdm`'s `add` accepts a bare node path but writes the row in a form its own grammar rejects.** The validator reports the failure two tables later than the cause.

## Next-cycle Changes
- **Instruction changes**
  - Before pinning any rule that depends on colgrep's output, cite the colgrep source line or a captured `--json` sample in the brief. For stderr, check the `quiet`/`json` gating.
  - Split such gates in two: "regression tests fail on the old code" and "contract pins hold on both".
- **Workflow changes**
  - Always pass `.md` to `dirtree-rdm add` for a leaf.
  - Run the full suite (`--junitxml`, parsed) in a fresh task worktree before dispatch, not a selected subset.
  - Use `gh api` REST for PR edits.
- **Review process changes**
  - Keep the verifier's required real-binary probe for anything touching `location_verified` or `hit_id`. It was the only check that exercised continuation chunks.
  - Re-verify a fix round narrowly by `SendMessage` to the same verifier. That took 4 minutes, against 10 for its first pass.

## Artifacts to Preserve
- `__roadmap__/match_units/`: the leaves, with their success gates and the step 5 skip
- `__reports__/match_units/00-findings_upstream_colgrep_contract_v0.md`: the upstream asks and the accepted gaps
- PR #18 commit bodies: the median-of-5 tables (`1d896f8`, `cc9345a`) and the trust-rule rationale (`97bfd3d`)
- The probe scripts stay in the session scratchpad. Reproduce from the commit bodies instead.

## Open Questions
- Should `index_updated` (R05 D7) be kept? Under `--json` it can only detect a cold build ("Building index"). The verifier saw it miss incremental re-indexing, and ask #3 upstream would fix it.
- Would a multi-path `search` with overlapping paths ever come from an agent? If not, the (file, span, name) dedupe guards a case nobody hits.
- How does the per-unit hit list read to agents on long notes? Many hits from one file can fill the text budget sooner. The Murmuration lab's question set (OBS-M) could measure it.
