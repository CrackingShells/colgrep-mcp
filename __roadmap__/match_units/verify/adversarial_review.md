# Adversarial Review

**Goal**: Find what is wrong in `unit_pipeline` before it merges: silent location and trust failures, the class of bug a green suite does not show.
**Pre-conditions**:
- [x] `unit_pipeline` has reported, with its gates green on `task/match-units-pipeline`
- [x] `colgrep --version` reports 1.8.4 or newer, and the scratch copy of a notes corpus named in the verifier's brief exists outside this repository
**Success Gates**:
- ✅ A findings list in which each attack below is marked broken (with a reproducer) or held (with the probe that tried to break it) [behavioral]
- ✅ The real-binary probe: the wave-05 105-156 hit is `location_verified` and `expand` returns line 138 [run]
- ✅ The share of leaders verified by exact span versus whole-file fallback, over 3–5 statera queries, is reported [run]
**References**: [R01 §Verdict on c4c291a, §Target design](~/.claude/plans/now-switching-you-to-tidy-glade.md) — the rules under attack

## Step 1: Attack the pipeline and probe the real binary
**Goal**: Assume the change is wrong and try to prove it.
**Implementation Logic**:
Read-only. Write probes in the scratchpad, not in the repo. Attack:
- **Trust-rule false positives:** edits between units, renamed headings, dotted, duplicate and emphasised headings, CRLF files.
- **Exact-span false positives:** the same code at another location in the file.
- **Line counting:** `islice` versus `splitlines()` on files containing `\f`, `\x0b` or U+2028.
- **The prefix cut:** behaviour with tied scores.
- **`hit_id`s:** overlapping or inverted ranges.
- **Counts:** do `find_files` and `search` agree on how many units a file has?
- **`expand` grouping:** input order, duplicate ids, an unreadable file.
- **Step 5's `-k` evidence**, if that step landed.

Then run this tree's server against the real binary: `COLGREP_DATA_DIR` and `COLGREP_MCP_ROOT` set to the scratch data dir and corpus named in the brief. Use 3–5 queries, including "what did the PI decide about w05-c1's escalation to switch to a subagent worker". Never point it at this repository.
**Deliverables**: the findings list in the verifier's report; probe scripts stay in the scratchpad
**Consistency Checks**: `colgrep --version` (expected: PASS)
**Commit**: `test(search): none — read-only review, findings go to the implementer`
