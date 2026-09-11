# End-to-End Validation

**Goal**: Run the assembled server against the real `colgrep` binary on a real repository through the stdio transport, measure, and record a findings report the PI can read in five minutes.
**Pre-conditions**:
- [ ] `server_assembly` merged; real `colgrep` on PATH; a real corpus available: clone `https://github.com/pallets/click` shallowly into `~/Documents/explore/_colgrep_e2e_corpus/click` — NOT under `/private/tmp` (R05 D3: a shared colgrep project is rooted there)
**Success Gates**:
- ✅ [behavioral] `__reports__/colgrep_mcp/02-findings_e2e_validation_v0.md` exists with a Results Table of ≥ 10 tool calls (tool, arguments, wall time, hits, text chars, truncated) and a Headline Result of median warm `search` latency
- ✅ [behavioral] `index_build` on the corpus completes through the server with ≥ 1 progress notification observed by the client script
- ✅ [behavioral] `claude --plugin-dir . -p "Use the colgrep search tool to find where <corpus concept> is implemented; cite file:line"` (with cwd = corpus) produces an answer citing a file that exists — or the report states exactly why it could not be run
- ✅ [static] Any defect found is filed as an `observation` report or fixed in a `fix(...)` commit on this branch with a test
**References**: [R01 §Risks & Mitigations](../../../../../../__reports__/colgrep_mcp/00-architecture_v0.md) — risks 1, 3, 5 are what this leaf tests; [R03](../../../../../../__reports__/colgrep_mcp/01-findings_colgrep_behaviour_v0.md) — expected latencies

## Step 1: Scripted stdio session against the real binary
**Goal**: Numbers, not vibes.
**Implementation Logic**:
Write `server/tests/e2e/run_e2e.py` (not collected by pytest; documented in README Development): connects over stdio to `uv run colgrep-mcp` with `COLGREP_MCP_ROOT=<corpus>`, then runs in order: `doctor`; `index_status`; `index_build` (progress callback counts notifications, records wall time); `index_status` again; 6 × `search` with varied arguments (semantic only; with `pattern`; with `include=["*.py"]`; `limit=None`; `include_code=True, limit=3`; a nonsense query); `find_files`; `expand` on the top 3 hit_ids of the first search; `list_indexes`; read `colgrep://guide` and `colgrep://status/<corpus>`; `get_prompt("explore")`. Records per call: wall ms, `is_error`, hit count, text length, `truncated`. Writes a Markdown table to stdout. Run it twice (cold after `colgrep clear <corpus>` — only if `colgrep status <corpus>` reports `Project:` equal to the corpus path itself, R05 D3 — then warm). Then attempt the `claude --plugin-dir` behavioural gate with a 180 s timeout. Fix any defect found (with a regression test) in a separate `fix(<scope>): …` commit before the report commit. Finally `colgrep clear <corpus>`.
**References**: [R01 §Token-budget invariant](../../../../../../__reports__/colgrep_mcp/00-architecture_v0.md) — verify the cap held on the exhaustive search
**Deliverables**: `server/tests/e2e/run_e2e.py`, `__reports__/colgrep_mcp/02-findings_e2e_validation_v0.md`, `__reports__/colgrep_mcp/README.md` (round 02 entry), optional `fix(...)` commits
**Consistency Checks**: `cd server && uv run python tests/e2e/run_e2e.py --corpus <path> --dry-run` (expected: PASS)
**Commit**: `docs(reports): record end-to-end validation of colgrep-mcp against a real repository`
