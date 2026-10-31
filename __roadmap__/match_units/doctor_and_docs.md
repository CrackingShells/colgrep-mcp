# Doctor and Docs

**Goal**: Declare colgrep 1.8.4 the soft minimum through `doctor`, and state the one-hit-per-unit rule by editing the guide in place rather than appending to it.
**Pre-conditions**:
- [ ] The roadmap commit is on `claude/happy-hamilton-e15dcd`
**Success Gates**:
- ⬜ `cd server && uv run pytest -q tests/test_tools_index.py tests/test_adapter.py` passes [run]
- ⬜ `git diff main..HEAD -- skills/` is empty [run]
- ⬜ `git diff --numstat main..HEAD -- server/colgrep_mcp/guide.md` adds no more than 4 lines net [run]
- ⬜ `AGENTS.md` names `OBS-M` and points it at `__reports__/match_lines/00-observation_markdown_match_lines_v0.md` [run]
**References**: [R01 §Documentation, §Minimum colgrep 1.8.4](~/.claude/plans/now-switching-you-to-tidy-glade.md) — what to revert, what to rewrite, how strict the minimum is

## Step 1: Report a colgrep older than 1.8.4 in doctor
**Goal**: `doctor` names an old binary as a problem with a version-neutral upgrade hint.
**Implementation Logic**:
colgrep 1.8.4 (upstream 1af6b16) is the first release with `matches`, and the user set it as the minimum, softly.
- Parse the first `(\d+)\.(\d+)\.(\d+)` of `colgrep --version` and compare it as a tuple. `1.8.5+cs.1` is fine, `1.10.0` is newer than `1.8.4`, and unparsable output raises no problem.
- An older version adds a problem stating the minimum and that `search` then falls back to slower whole-file location. The hint must not say `colgrep update`: on this machine that would replace the fork.
- Move the fake's `--version` to `colgrep 1.8.5`, and update the two assertions that pin the old string (`test_adapter.py`, `test_tools_index.py`).
- Add a parametrized parse test.
- In the README requirements table, change the cell `colgrep ≥ 1.6` to `≥ 1.8.4`.
**Deliverables**: `server/colgrep_mcp/tools_index.py` — `MIN_COLGREP` and the version check in `doctor`; `server/tests/fake_colgrep.py` — `--version` line; `server/tests/test_adapter.py`, `server/tests/test_tools_index.py` — assertions and parse test; `README.md` — one table cell
**Consistency Checks**: `cd server && uv run pytest -q tests/test_tools_index.py tests/test_adapter.py` (expected: PASS)
**Commit**: `feat(index): report a colgrep older than 1.8.4 in doctor`

## Step 2: State the one-hit-per-unit rule in place
**Goal**: The guide states exactly the rule `unit_pipeline` implements, with nothing appended, and the skill keeps the text it had on `main`.
**Implementation Logic**:
- Revert `skills/colgrep-search/SKILL.md` to `main`. The clause added in c4c291a was defensive, and the skill already defers to the guide.
- In `guide.md`:
  - Drop the paragraph c4c291a appended.
  - Extend the existing "A hit is one unit…" sentence by one clause: one hit per matched unit, ranked with every other file's hits.
  - Rewrite the `location_verified` paragraph as one statement of the final rule. That rule covers: a leader verified against its own lines, falling back to whole-file location; a later unit trusted through its leader and its heading line; and an unverified later unit carrying no snippet. The "colgrep 1.6 itself…" history goes.
  - The `truncated` sentence says only what the server can know: its own cut to `limit`, or the text budget.
- Add the `OBS-M` legend row to `AGENTS.md`.

Write this after `unit_pipeline` reports, so the wording matches the code.
**Deliverables**: `skills/colgrep-search/SKILL.md` — reverted; `server/colgrep_mcp/guide.md` — the paragraphs above; `AGENTS.md` — one legend row
**Consistency Checks**: `git diff --quiet main -- skills/` (expected: PASS)
**Commit**: `docs(resources): state the one-hit-per-unit rule in place`
