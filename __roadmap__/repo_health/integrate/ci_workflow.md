# CI Workflow

**Goal**: Run the gate commands on every push and pull request across the three operating systems, so the cross-platform claim of the launcher is checked by a machine rather than asserted.
**Pre-conditions**:
- [ ] `python_tooling` merged (ruff and commitizen exist in the dev group)
**Success Gates**:
- ✅ [static] `.github/workflows/ci.yml` exists, parses as YAML, and calls only `uv sync`, `uv run ruff check`, `uv run pytest`, `uv run cz check`
- ✅ [static] the test job matrix covers `ubuntu-latest`, `macos-latest`, `windows-latest`
**References**: [R01 §C2 enforcement model, §C5](../../../__reports__/repo_health/00-architecture_v0.md)

## Step 1: Add the workflow
**Goal**: A minimal, readable workflow an agent can extend.
**Implementation Logic**:
Lead-authored. Two jobs. `test`: matrix over the three OSes with Python from `server/.python-version` via `astral-sh/setup-uv` (`enable-cache: true`), steps `uv sync --directory server`, `uv run --directory server ruff check`, `uv run --directory server pytest`. `commits`: `ubuntu-latest`, `fetch-depth: 0`, on pull requests only, `uv run --directory server cz check --rev-range origin/${{ github.base_ref }}..HEAD`. Triggers: push to `main`, pull_request. Validate with `actionlint` if installed, else `python -c 'import yaml; yaml.safe_load(...)'`. No release job: releases are cut locally with `cz bump` by design (no remote yet); say so in a comment at the top.
**Deliverables**: `.github/workflows/ci.yml` (jobs `test`, `commits`)
**Consistency Checks**: `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml'))"` (expected: PASS)
**Commit**: `build(repo): add a cross-OS CI workflow running ruff, pytest and cz check`
