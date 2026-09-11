# Error and Hint Taxonomy

**Goal**: Give every failure and every degraded success a stable, machine-readable code that names the next usage pattern, so agents recover by rule instead of by guessing.
**Pre-conditions**:
- [ ] `build/tools/search_tools` and `index_tools` merged (all `ToolError` sites and `notes` producers exist)
**Success Gates**:
- ✅ [static] `server/colgrep_mcp/errors.py` defines `class Code(StrEnum)` with exactly: `NO_HITS`, `LIMIT_DEFAULT_APPLIED`, `TEXT_TRUNCATED`, `LOCATION_UNVERIFIED`, `INDEX_COLD`, `PATH_NOT_FOUND`, `PROJECT_ROOT_MISMATCH`, `CONFIRMATION_REQUIRED`, `COLGREP_MISSING`, `COLGREP_FAILED`, `COLGREP_TIMEOUT`, `BAD_HIT_ID`, and a `HINTS: dict[Code, str]` mapping each to a one-sentence next step
- ✅ [run] `cd server && uv run pytest -q tests/test_errors.py` passes: every `ToolError` raised by the tools has a message starting with `[<CODE>] ` and ending with `Next: <hint>`; every note in `SearchResult.notes` starts with `[<CODE>] `
- ✅ [run] `read_resource("colgrep://errors")` returns Markdown listing every code with its hint; `test_errors.py` asserts the set equals `Code`
- ✅ [static] `guide.md` has a "Codes" section linking to `colgrep://errors`
**References**: [R01 §Error model](../../../../../__reports__/colgrep_mcp/00-architecture_v0.md); [R05 D5, D6](../../../../../__reports__/colgrep_mcp/02-architecture_v1.md); PI request (2026-09-12, mid-run): "standardized tool call error code that can point the agents toward different usage patterns"

## Step 1: Define codes and route every error and note through them
**Goal**: One module owns the vocabulary; tools only pick a code.
**Implementation Logic**:
`errors.py`: `Code(StrEnum)`; `HINTS`; `def tool_error(code: Code, detail: str) -> ToolError` producing `f"[{code}] {detail} Next: {HINTS[code]}"`; `def note(code: Code, detail: str = "") -> str` producing `f"[{code}] {detail or HINTS[code]}"`; `def from_adapter_error(exc: ColgrepError, *, path: Path | None) -> ToolError` mapping `ColgrepNotFound→COLGREP_MISSING`, `ColgrepTimeout→INDEX_COLD` when `path` is not indexed per a cheap `status` check is NOT possible inside a mapper — so: `ColgrepTimeout→COLGREP_TIMEOUT` with the INDEX_COLD hint appended when the caller passes `indexed=False`, `ColgrepFailed` whose stderr contains `Path does not exist`→`PATH_NOT_FOUND` (include colgrep's closest-directory hint verbatim), else `COLGREP_FAILED`. Replace every ad-hoc `ToolError(...)` in `tools_search.py`, `tools_index.py`, `paths.py` and every `ResourceError` in `resources.py` with the helpers; replace ad-hoc `notes` strings with `note(...)`. `expand` with a malformed id → `BAD_HIT_ID` per-unit error string using the same prefix. Add `colgrep://errors` resource (text/markdown) rendered from `HINTS`, and a "Codes" section in `guide.md`. Tests: parametrise over each tool's failure path with the fake binary (`FAKE_COLGREP_EXIT`, missing binary, bad path, mismatch root via `FAKE_COLGREP_PROJECT_ROOT` env — add that knob to `fake_colgrep.py` so `status` reports a different `Project:`), assert prefix/suffix; assert notes prefixes; assert the resource lists all codes.
**References**: [R01 §Error model](../../../../../__reports__/colgrep_mcp/00-architecture_v0.md) — conditions to cover
**Deliverables**: `server/colgrep_mcp/errors.py` (`Code`, `HINTS`, `tool_error`, `note`, `from_adapter_error`), `server/colgrep_mcp/resources.py` (`errors_resource`), `server/colgrep_mcp/guide.md` (Codes section), edits in `tools_search.py`, `tools_index.py`, `paths.py`, `server/tests/test_errors.py`, `server/tests/fake_colgrep.py` (`FAKE_COLGREP_PROJECT_ROOT`)
**Consistency Checks**: `cd server && uv run pytest -q tests/test_errors.py` (expected: PASS)
**Commit**: `feat(server): add coded errors and hints that steer agents to the next search pattern`
