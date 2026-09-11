# Package Scaffold

**Goal**: Stand up the `server/` Python package skeleton, test harness with a fake colgrep, and repo-level release files so every later leaf edits files that already exist and imports that already resolve.
**Pre-conditions**:
- [ ] R01 architecture report present (`__reports__/colgrep_mcp/00-architecture_v0.md`)
- [ ] `uv` on PATH
**Success Gates**:
- ✅ [run] `cd server && uv run python -c "import colgrep_mcp, mcp; print(colgrep_mcp.__version__)"` prints `0.1.0`
- ✅ [run] `cd server && uv run pytest -q` passes (smoke test that the fake colgrep runs and the server object exists)
- ✅ [static] `CHANGELOG.md` has an `Unreleased` section; `LICENSE` is MIT
**References**: [R01 §Packaging layout](../../__reports__/colgrep_mcp/00-architecture_v0.md) — file tree and dependency list

## Step 1: Create the package, test harness and release files
**Goal**: One commit that turns the repo from prose into an installable (empty) server.
**Implementation Logic**:
1. `server/pyproject.toml` (hatchling build backend; `name = "colgrep-mcp"`, `version = "0.1.0"`, `requires-python = ">=3.11"`, deps `mcp>=2.2,<3`, `pydantic>=2`; dev group `pytest`, `pytest-asyncio`/`anyio`, `inline-snapshot`; `[project.scripts] colgrep-mcp = "colgrep_mcp.__main__:main"`; pytest config `asyncio_mode = "auto"`). `server/.python-version` = `3.12`.
2. Package modules as empty-but-importable stubs with module docstrings and the public names from R01 declared (`adapter.py`: exception classes + `ColgrepAdapter` class with `NotImplementedError` bodies; `models.py`: the Pydantic models verbatim from R01; `config.py`: `Settings` dataclass reading the env vars in R01 §Configuration; `server.py`: `mcp = MCPServer("colgrep", instructions=INSTRUCTIONS)` with the instructions text; `__main__.py`: `main()` parsing `--transport/--host/--port` and calling `mcp.run`; `textparse.py`, `tools_search.py`, `tools_index.py`, `resources.py`, `prompts.py`: docstring + `register(mcp)` no-op).
3. `server/tests/fake_colgrep.py`: an executable Python script emulating colgrep's CLI surface for tests — `--version`, `--json` search (returns fixture hits from `tests/fixtures/hits_small.json`, honouring `-k`), `status PATH`, `--stats`, `settings`, `init -y PATH` (prints 3 progress lines to stderr), `clear PATH`; all output plain text; exit codes 0/1/2 controllable via env `FAKE_COLGREP_EXIT`. `tests/conftest.py` exposes fixture `fake_colgrep_bin` (path, chmod +x) and `settings_env` (monkeypatches `COLGREP_MCP_BINARY`).
4. `server/tests/test_smoke.py`: (a) fake binary runs and emits JSON; (b) `Client(mcp)` initializes and `list_tools()` returns a list (may be empty).
5. Repo root: `CHANGELOG.md` (Keep a Changelog header + `## [Unreleased]`), `LICENSE` (MIT, Eliott Jacopin, 2026), `.gitignore` additions for `server/.venv`, `uv.lock` committed.
**References**: [R01 §Pydantic models](../../__reports__/colgrep_mcp/00-architecture_v0.md) — copy the model fields exactly; [R01 §Adapter contract](../../__reports__/colgrep_mcp/00-architecture_v0.md) — method names
**Deliverables**: `server/pyproject.toml`, `server/.python-version`, `server/uv.lock`, `server/colgrep_mcp/__init__.py` (`__version__`), `server/colgrep_mcp/{__main__,server,config,adapter,textparse,models,tools_search,tools_index,resources,prompts}.py`, `server/tests/{conftest.py,fake_colgrep.py,test_smoke.py}`, `server/tests/fixtures/hits_small.json`, `CHANGELOG.md`, `LICENSE`
**Consistency Checks**: `cd server && uv run pytest -q` (expected: PASS)
**Commit**: `build(repo): scaffold colgrep-mcp package, fake-colgrep test harness and release files`
