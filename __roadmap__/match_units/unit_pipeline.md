# Unit Pipeline

**Goal**: Rebuild `search`'s hit construction as one output-proportional pipeline: adapter JSON → `unit_matches` → rank and cut to `limit` → read only the surviving spans → build hits. Every unit keeps its own verified range and name.
**Pre-conditions**:
- [x] Task branch `task/match-units-pipeline` is cut from `claude/happy-hamilton-e15dcd` at the commit that adds this roadmap
- [x] `cd server && uv run pytest -q` is green in the task worktree before any edit
**Success Gates**:
- ✅ `cd server && uv run pytest -q && uv run ruff check && uv run ruff format --check && uv run cz check --rev-range claude/happy-hamilton-e15dcd..HEAD` passes [run]
- ✅ Only `adapter.py` reads `matches`: within `server/colgrep_mcp/`, only `adapter.py` contains the string `"matches"` [run]
- ✅ `FAKE_COLGREP_MATCHES` no longer appears under `server/` [run]
- ⬜ Every new contract test named in steps 1–4 fails when `server/colgrep_mcp/` is checked out at c4c291a, and the report lists them [run]
- ✅ The bodies of commits 3 and 4 carry median-of-5 before/after tables, or the commit is typed `refactor` and the report says why [run]
**References**: [R01 §Verdict on c4c291a, §Target design](~/.claude/plans/now-switching-you-to-tidy-glade.md) — the nine findings this leaf answers (rows 1–7, 9) and the design it implements

## Step 1: Normalise colgrep results to leader-first unit matches
**Goal**: Make `adapter.unit_matches` the only reader of the `matches` wire shape, and feed the tests literal colgrep 1.8 JSON.
**Implementation Logic**:
colgrep returns one result per file (`collapse_by_file`, `colgrep/src/index/mod.rs`). Since 1.8.4, `matches: [{line, end_line, name, score}]` lists each matched unit, best first. It appears only when two or more matched, and `matches[0]` is the leader. Today `hits_from_raw` and `_file_hits_from_raw` each re-derive this, and they diverge: `search` dedupes, `find_files` does not (verdict row 1). colgrep's own idiom is `SearchResult::unit_matches()`.

- **The type.** Add `UnitMatch(NamedTuple)` with `line`, `end_line`, `name`, `score`, next to `RawHit` in `adapter.py`. That file is the colgrep wire boundary.
- **The normaliser.** Add `unit_matches(raw) -> list[UnitMatch]`:
  - It returns a leader-first list.
  - It dedupes on `(line, end_line)` with max score, as colgrep's `absorb_matches` does.
  - It stable-sorts the non-leaders by score descending, which enforces the prefix-cut invariant step 3 relies on.
  - It drops entries that violate `1 <= line <= end_line`.
  - When `matches` is absent or has one entry, it returns `[UnitMatch(unit.line, unit.end_line, unit.name, score)]`.
- **Callers.** `hits_from_raw` and `_file_hits_from_raw` go through it, with behaviour otherwise unchanged in this step. `find_files` counts the deduped units and drops empty names from `top_units`.
- **Fake and fixtures.**
  - Drop the `FAKE_COLGREP_MATCHES` knob and `_collapse_by_file` from `fake_colgrep.py` (verdict row 9). Its docstring says a fixture's `matches` passes through verbatim, and that `-k` counts files because results are already per file.
  - Convert `fixtures/hits_small.json` to the 1.8 shape: one result for `config.py`, with `matches` listing `parse_config` and `Settings`, then one for `README.md`. Its consumers must keep their counts: `total == 3`, and `find_files` `hits == 2` for `config.py`.
  - Rewrite the four existing `matches` tests in `test_tools_search.py` on literal 1.8-shaped fixtures, ordered best first.
- **New contract test.** Duplicate ranges in `matches` yield one hit in `search` and one count in `find_files`.

Leave the `--version` line in `fake_colgrep.py` alone. The coordinator changes it in `doctor_and_docs` on the integration branch.
**Deliverables**: `server/colgrep_mcp/adapter.py` — `UnitMatch`, `unit_matches`; `server/colgrep_mcp/tools_search.py` — `hits_from_raw`, `_file_hits_from_raw` calling `unit_matches`; `server/tests/fake_colgrep.py` — knob and `_collapse_by_file` removed; `server/tests/fixtures/hits_small.json` — 1.8 shape; `server/tests/test_tools_search.py` — literal fixtures, dedupe test
**Consistency Checks**: `cd server && uv run pytest -q tests/test_tools_search.py tests/test_render.py tests/test_smoke.py` (expected: PASS)
**Commit**: `refactor(adapter): normalise colgrep results to leader-first unit matches`

## Step 2: Keep each unit to its own verified range and name
**Goal**: Fix the three location bugs and the naming mix in one builder (verdict rows 2, 3, 4, 6, 7).
**Implementation Logic**:
- **Row 2.** `hit_from_raw` takes the leader's `UnitMatch` and passes its range to `locate_unit` as the reported range. Today that range is the widened `unit.line..end_line`, so an unlocatable leader's `hit_id` overlaps every sibling.
- **Rows 3 and 4.** One private builder serves every non-leader, replacing the second 12-kwarg `SearchHit(...)` block.
  - A non-leader is trusted only when the leader was verified exactly at `matches[0]`'s range **and** the last dotted segment of the match name (`name.rsplit(".", 1)[-1]`) occurs in the file's line `line`.
  - **Nameless non-leaders fail closed.** colgrep gives `document` and `raw_code` units an empty name.
  - An untrusted non-leader gets `snippet=None` and `code=None`, never text sliced at moved lines.
  - The `location_verified` field description in `models.py` states this rule.
- **Row 6.** When `matches` is present, every hit of that file takes colgrep's display name, the leader included. The leader keeps `qualified_name`, `unit_type` and `signature` from `unit`. Output without `matches` is unchanged.
- **Row 7.** Pin the signature-less head in `test_render.py`: no trailing ` — `.
- **New contract tests** through `Client(build())`:
  - an edit below the leader: the sibling is unverified, with no snippet;
  - an unlocatable leader: its own range, not the widened span;
  - a nameless sibling: unverified;
  - `include_code` on a trusted non-leader;
  - a one-entry `matches`;
  - a heading containing a dot (`## v1.8 notes`), which stays trusted.
**Deliverables**: `server/colgrep_mcp/tools_search.py` — `hit_from_raw` taking the leader `UnitMatch`, one non-leader builder; `server/colgrep_mcp/models.py` — `location_verified` description; `server/tests/test_tools_search.py`, `server/tests/test_render.py` — the tests above
**Consistency Checks**: `cd server && uv run pytest -q tests/test_tools_search.py tests/test_render.py` (expected: PASS)
**Commit**: `fix(search): keep each unit to its own verified range and name`

## Step 3: Build only surviving units and verify leaders by exact span
**Goal**: Make `search`'s work proportional to the hits it returns, not to the files and units colgrep sent (verdict row 5).
**Implementation Logic**:
- **Rank and cut first.** `_do_search` stable-sorts `(score, result index, match index)` over every `unit_matches` list and cuts to `limit` before building anything. A file's survivors are a prefix of its list, so its leader is always built.
- **The cache** is pinned so the builder stays pure and I/O-free.
  - An async step replaces `_fill_file_cache`. For each file with survivors it reads only those spans in **one** `itertools.islice` pass, up to the largest surviving `end_line`, in `asyncio.to_thread`, with one `gather` across files. This generalises `_read_span` into `_read_spans(file, spans) -> dict[(line, end_line), list[str]]`; `expand` reuses it in step 4.
  - The builder receives `file -> {span: lines}` plus an optional full text.
- **Exact-span verification.** A leader whose range has exactly as many lines as its `code` is verified by comparing that span to `code`. The comparison uses the trailing-whitespace (`rstrip`) normalisation, factored out of `locate.py` into one helper both paths call.
  - Only on a mismatch, or when the lengths differ, is the whole file read once and `locate_unit` run. That happens for a file edited since indexing, or a pre-1.8.4 binary whose range is widened.
  - Say in the docstring that a trailing-whitespace-only edit now verifies.
- **Tests.**
  - A spy test pins that a span-verified leader never triggers a whole-file read, in the style of `test_find_files_does_not_read_hit_files`.
  - Switch `test_search_reads_hit_files_off_the_event_loop` to spy on `open`, as the `expand` test does. With exact spans, the happy path never calls `read_text`, so the old spy would stop testing what it names.
  - Adapt the `_fill_file_cache` tests to the new step.
- **Measurement** (`perf` rule, maintainer-policy):
  - Corpus: 15 markdown files of 2,000 lines each, with 30 matched sections per file, plus a matching fixture, all in the scratchpad.
  - Harness: a stub adapter like `_StderrInjectingAdapter`, timing the post-adapter part of `_do_search` at `limit=15` and `limit=None`.
  - Run: median of 5, at step 2's commit versus this one.
  - Record the table in the body. If the numbers don't show a gain, type the commit `refactor` and say so.
**Deliverables**: `server/colgrep_mcp/tools_search.py` — rank-and-cut in `_do_search`, `_read_spans`, span cache step replacing `_fill_file_cache`; `server/colgrep_mcp/locate.py` — the shared normalised-comparison helper; tests above; benchmark script kept in the scratchpad, not committed
**Consistency Checks**: `cd server && uv run pytest -q` (expected: PASS)
**Commit**: `perf(search): build only surviving units and verify leaders by exact span`

## Step 4: Read each file's expanded spans in one pass
**Goal**: `expand` reads a file once however many of its `hit_id`s it is given (verdict row 5).
**Implementation Logic**:
Per-unit hits make several `hit_id`s of one file the common case, and `expand` opens and `islice`s the file once per id.

- Group the parsed ids by file and make one `_read_spans` pass per file, off the loop as today.
- Emit units in input order.
- Malformed-id errors stay per unit. An `OSError` attaches to every id of that file.
- Overlapping and non-contiguous spans must both work.
- **Contract test:** three ids of one file, out of order and one overlapping, return the right spans in input order with one `open` (spy).
- **Measurement:** median of 5 for `expand` on 5 ids of one 2,000-line file, before and after, in the body.
**Deliverables**: `server/colgrep_mcp/tools_search.py` — `expand` grouped by file over `_read_spans`; `server/tests/test_tools_search.py` — the test above
**Consistency Checks**: `cd server && uv run pytest -q tests/test_tools_search.py` (expected: PASS)
**Commit**: `perf(search): read each file's expanded spans in one pass`

## Step 5: Ask colgrep for limit files in find_files
**Goal**: Stop `find_files` asking colgrep to rank and serialise three times the files it returns.
**Implementation Logic**:
`find_files` passes `-k min(limit * 3, 300)`. That over-fetch dates from when hits were per unit. Every supported colgrep returns one result per file.

- **Condition.** First confirm in colgrep's source that a search over several paths is collapsed globally, not per path. The fork's source is checked out under `~/.cargo/git/checkouts/next-plaid-e20e6e3a2c4603c9/7f1e855/colgrep/src/`; read `index/mod.rs` `collapse_by_file` and its caller in `commands/search.rs`.
- **If it is collapsed globally:** pass `-k limit`, keep the four-line cross-result fold, and pin the argv in a test.
- **If it is not:** keep `limit * 3`, skip this commit, and report what the source shows.

This cost lies inside colgrep, beyond the in-process stub, so the commit is a `refactor`, not a measured `perf`.
**Deliverables**: `server/colgrep_mcp/tools_search.py` — `find_files` `hit_limit`; `server/tests/test_tools_search.py` — argv test
**Consistency Checks**: `cd server && uv run pytest -q tests/test_tools_search.py` (expected: PASS)
**Commit**: `refactor(search): ask colgrep for limit files in find_files`
