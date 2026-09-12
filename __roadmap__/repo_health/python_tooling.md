# Python Tooling: Version Source, Commitizen, Ruff

**Goal**: Make `server/pyproject.toml` the single version source, encode the CONTRIBUTING commit vocabulary as commitizen machinery that bumps, tags and writes the changelog, and add a `ruff check` gate.
**Pre-conditions**:
- [ ] Branch `task/python_tooling` created from the campaign branch `claude/mcp-server-repo-health-e13188`
- [ ] `cd server && uv run pytest` passes before any change (193 passed, 1 skipped)
- [ ] `uvx --from commitizen cz version` prints ≥ 4.18
**Success Gates**:
- ✅ [run] `cd server && uv run pytest` passes, including new `tests/test_version.py`
- ✅ [run] `cd server && uv run ruff check` exits 0
- ✅ [run] `cd server && uv run cz check --rev-range v0.1.0..HEAD` exits 0 over this branch's own commits
- ✅ [run] `cd server && uv run cz bump --dry-run` prints a next version and lists `pyproject.toml`, the three manifests and `../CHANGELOG.md` as files it would touch; it must NOT actually change anything
- ✅ [static] `server/colgrep_mcp/__init__.py` contains no literal version string
- ✅ [static] `CONTRIBUTING.md` §Versioning describes `cz check` / `cz bump` as the machinery and says enforcement is CI-only
**References**: [R01 §C1, §C2, §C5, Risks 2 and 5](../../__reports__/repo_health/00-architecture_v0.md) — contracts this leaf implements; [R04 CONTRIBUTING](../../CONTRIBUTING.md) — the vocabulary to encode verbatim

## Step 1: Derive `__version__` from package metadata
**Goal**: Stop hand-copying the version into `__init__.py`.
**Implementation Logic**:
Replace the literal in `server/colgrep_mcp/__init__.py` with `importlib.metadata.version("colgrep-mcp")`, catching `PackageNotFoundError` and falling back to `"0.0.0+unknown"` with a comment saying when that can happen (source tree never installed). `uv run` installs the project editable, so under every documented command the metadata exists. Add `server/tests/test_version.py` that reads `[project].version` from `server/pyproject.toml` with `tomllib` and asserts equality with `colgrep_mcp.__version__` and with each of the three manifests' `version` fields (`plugin.json`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`). Do NOT edit `server/tests/test_manifests.py` (owned by the sibling leaf `launcher`); its `test_versions_aligned` may stay as is. Run the suite: `test_smoke.py` compares `server_info.version` to `__version__`, so it must still pass.
**Deliverables**: `server/colgrep_mcp/__init__.py` (`__version__` via `importlib.metadata`, fallback constant), `server/tests/test_version.py` (`test_version_matches_pyproject`, `test_manifests_match_pyproject`, helper `_pyproject_version`)
**Consistency Checks**: `cd server && uv run pytest -q tests/test_version.py tests/test_smoke.py tests/test_manifests.py` (expected: PASS); `! grep -q '0\.1\.0' server/colgrep_mcp/__init__.py` (expected: PASS)
**Commit**: `refactor(server): read __version__ from package metadata instead of a hand-copied literal`

## Step 2: Configure commitizen to the CONTRIBUTING vocabulary
**Goal**: Turn the prose convention into machinery that can check commits, bump the version everywhere, and write the changelog.
**Implementation Logic**:
Add `commitizen` to the `dev` dependency group (`uv add --dev commitizen`, which updates `uv.lock`). Add `[tool.commitizen]` to `server/pyproject.toml`, run from `server/` like every other command in this repo: `name = "cz_customize"`, `version_provider = "pep621"`, `tag_format = "v$version"`, `bump_message = "release(colgrep-mcp): v$new_version"`, `update_changelog_on_bump = true`, `changelog_incremental = true`, `changelog_file = "../CHANGELOG.md"`, `version_files` covering `../plugin.json:"version"`, `../.claude-plugin/plugin.json:"version"`, `../.codex-plugin/plugin.json:"version"` (verify the exact `path:pattern` syntax in the commitizen docs; use the context7 MCP tools or WebFetch on commitizen-tools.github.io). Under `[tool.commitizen.customize]` encode exactly the CONTRIBUTING table: `schema_pattern` requiring `type(scope): description` with the scope MANDATORY and types limited to `feat fix refactor perf test docs build chore release`; `bump_pattern`/`bump_map` giving feat→MINOR, fix→PATCH, perf→PATCH, `BREAKING CHANGE`→MAJOR (do not set `major_version_zero`; CONTRIBUTING says breaking = major); `change_type_map` mapping feat→"Added", fix→"Fixed", perf→"Changed" so generated sections match the hand-written Keep-a-Changelog 0.1.0 entry; `changelog_pattern` limited to feat/fix/perf/breaking; `commit_parser` capturing type, scope, message; a minimal `message_template`/`questions` block if `cz_customize` requires one. Then measure: `uv run cz check --rev-range v0.1.0..HEAD` must pass; also run `uv run cz check --rev-range HEAD~74..HEAD` (the whole history) and record in the commit body how many commits fail and why (merge commits with custom subjects are the expected class — add `allowed_prefixes` only if the failing subjects share a literal prefix; never widen the type list to make old commits pass). Finally `uv run cz bump --dry-run` from `server/` must print the predicted version and touched files without writing anything; if it errors because no bump-worthy commit exists yet, record that output verbatim in the commit body and test the machinery instead with `uv run cz bump --dry-run --increment PATCH`.
**Deliverables**: `server/pyproject.toml` (`[tool.commitizen]`, `[tool.commitizen.customize]`, `commitizen` in `[dependency-groups].dev`), `server/uv.lock` (updated)
**Consistency Checks**: `cd server && uv run cz check --rev-range v0.1.0..HEAD` (expected: PASS); `cd server && uv run cz bump --dry-run --increment PATCH | grep -q '0.1.1'` (expected: PASS); `test -z "$(git status --porcelain plugin.json CHANGELOG.md .claude-plugin .codex-plugin)"` (expected: PASS)
**Commit**: `build(repo): encode the commit vocabulary as commitizen machinery for bump, tag and changelog`

## Step 3: Add a ruff check gate
**Goal**: Give agents a deterministic lint command whose clean state is the norm.
**Implementation Logic**:
`uv add --dev ruff`. Add `[tool.ruff]` with `line-length = 120`, `target-version = "py311"`, `src = ["."]`, `extend-exclude = [".venv"]`, and `[tool.ruff.lint] select = ["E", "F", "I", "UP", "B"]`. Run `uv run ruff check --fix` for safe fixes, then fix the remaining findings by hand with the smallest possible edits (a `# noqa: <code>` with a one-line reason is acceptable only where the code is deliberate, e.g. a broad `except` that must swallow). Do NOT run `ruff format` (R01 non-goal: a sibling leaf edits `tests/test_manifests.py` in parallel; format churn would conflict). If a finding is in `server/tests/test_manifests.py`, leave it and list it in the commit body for the lead to fix at integration. Re-run the full test suite after the fixes.
**Deliverables**: `server/pyproject.toml` (`[tool.ruff]`, `[tool.ruff.lint]`, `ruff` in dev group), `server/uv.lock`, minimal edits in `server/colgrep_mcp/*.py` and `server/tests/*.py` (except `test_manifests.py`)
**Consistency Checks**: `cd server && uv run ruff check` (expected: PASS, "All checks passed"); `cd server && uv run pytest -q` (expected: PASS)
**Commit**: `build(repo): add a ruff check gate and fix the findings it raises`

## Step 4: Document the machinery in CONTRIBUTING
**Goal**: Make the docs describe what the machinery enforces, so the two never disagree.
**Implementation Logic**:
Rewrite `CONTRIBUTING.md` §"Versioning and changelog": pyproject is the version source, `__version__` is derived, `cz bump` (run from `server/`) rewrites pyproject, the three manifests and `CHANGELOG.md` and tags `v<version>`; the release recipe is `cd server && uv run cz bump --changelog` followed by `uv sync` (R01 Risk 5) and `uv run pytest`. Add a short "Checks" subsection listing the gate commands: `uv run pytest`, `uv run ruff check`, `uv run cz check --rev-range main..HEAD`. State that enforcement is advisory locally and mandatory in CI (no git hook; agents commit). Add `release` to the types table as "bump commits only, written by `cz bump`". Keep the rest of the file as is.
**Deliverables**: `CONTRIBUTING.md` (§Versioning and changelog rewritten, §Checks added, `release` row)
**Consistency Checks**: `grep -q 'cz bump' CONTRIBUTING.md` (expected: PASS); `! grep -q 'is deferred until there is an external consumer' CONTRIBUTING.md` (expected: PASS)
**Commit**: `docs(docs): describe the commitizen release recipe and the gate commands in CONTRIBUTING`
