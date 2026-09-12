# repo_health — Observation (v0)

Date: 2026-09-12

---
type: observation
topic: repo_health
spotted-during: reviewer pass over the depth-0 merge (python_tooling + launcher) before the 0.1.1 release
date: 2026-09-12
domain: code
confidence: <overall: plausible>
urgency: <overall: medium>
deferred-because: read-only leaf; fixes are routed through integrate/release/cleanup_and_release.md
---

## What Was Noticed

1. `schema_pattern` in `server/pyproject.toml` has no end-of-string anchor, so the trailing `.+` swallows anything, including a trailing period. `chore(repo): tidy.` — the exact violation CONTRIBUTING.md calls out ("no trailing period") — passes `cz check` cleanly. The mandatory-scope and case rules are otherwise sound (all four case/scope probes rejected correctly). `[confidence: confirmed] [urgency: medium]`

2. The `bump_map` key `"^.+!$"` (meant to map a `feat(x)!` breaking-change shorthand to MAJOR) can never fire. Commitizen's `find_increment` extracts `found_keyword = result.group(1)` from `bump_pattern`, and `bump_pattern`'s first capture group only ever contains the bare type name (`feat`/`fix`/`perf`/`BREAKING CHANGE`) — the `!` lives in an separate, uncaptured-by-group(1) part of the match. Empirically, `feat(search)!: drop y` auto-bumps **MINOR**, not MAJOR, even though `cz check` happily accepts the `!` syntax as valid. The `BREAKING CHANGE:` footer path is unaffected and correctly bumps MAJOR. `[confidence: confirmed] [urgency: high]`

3. The changelog preview from `cz bump --dry-run --changelog` renders new entries as `## v0.1.1 (2026-09-12)`, while the hand-written `CHANGELOG.md` uses Keep-a-Changelog style `## [0.1.0] - 2026-09-12` (bracketed version, dash before date). Contract C2 says generated entries should "sit beside" the hand-written one; they will, but not in the same visual style. `[confidence: confirmed] [urgency: low]`

4. `.claude-plugin/mcp.json` sets `COLGREP_MCP_ROOT` from `${CLAUDE_PROJECT_DIR}`; the Agent Plugins 1.0 `mcp.json` has no equivalent env entry at all — not even a documented reason it's omitted. `test_manifests.py::test_mcp_configs_equivalent` never compares the two `env` blocks for parity; it only checks `agent_server`'s env keys against `FORBIDDEN_MCP_ENV_KEYS`, never `claude_server`'s. README §Configuration documents the asymmetry in passing ("the Claude Code plugin sets it to the project directory") but nothing pins it down as intentional-and-permanent versus a gap for Agent-Plugins-1.0 clients that lack a roots-based fallback. `[confidence: plausible] [urgency: medium]`

5. README.md is internally inconsistent about Windows support confidence: line 59 hedges ("though the server itself is untested there until CI says otherwise"), but the Packaging section (line 142) states flatly "this is true on Windows as well as macOS and Linux." No `.github/workflows/` exists yet in this diff (the `ci_workflow` leaf hasn't landed), so the flat claim currently overstates what has actually been verified. `[confidence: confirmed] [urgency: low]`

6. `version_files` patterns and the ruff-driven diffs check out clean — no findings, recorded for completeness. `version_files = ["../plugin.json:\"version\"", ...]`: commitizen's `update_version_in_files` only calls `line.replace(current_version, new_version)` on lines matching the literal `"version"` pattern (quotes included), and the only line in each manifest containing that literal substring is the actual `"version": "0.1.0"` field — the `$schema` URLs (containing `1.0.0`) never contain the substring `"version"`, so they're never touched. Every hand-made ruff fix inspected (`test_locks.py` E702 splits, `test_textparse.py` line wraps and the `l`→`ln` rename, the quote removal on `-> "ColgrepAdapter"` / `-> "Settings"` forward refs, import reordering/unused-import removal) is behavior-preserving. `[confidence: confirmed] [urgency: low]`

## Context

This is the reviewer pass (`__roadmap__/repo_health/integrate/review.md`) over the merged `python_tooling` + `launcher` leaves, checked against `__reports__/repo_health/00-architecture_v0.md` (contracts C1–C5, Risks 1–5) and `__reports__/repo_health/00-findings_launch_placeholders_v0.md`. `cd server && uv run pytest` passes (195 passed, 1 skipped), matching the environment note. `uv run ruff check` is clean. The material under review is `git diff v0.1.0..HEAD`.

## Location Map

- `server/pyproject.toml:55` — `schema_pattern` (finding 1)
- `server/pyproject.toml:57-58` — `bump_pattern` / `bump_map` (finding 2)
- `CHANGELOG.md:7-9` vs `cz bump --dry-run --changelog` output (finding 3)
- `.claude-plugin/mcp.json:6-8` vs `mcp.json:8-9`; `server/tests/test_manifests.py:117-118` (finding 4)
- `README.md:59` vs `README.md:142` (finding 5)
- `server/pyproject.toml:47-51` (version_files); `server/tests/test_locks.py`, `server/tests/test_textparse.py`, `server/colgrep_mcp/adapter.py:102`, `server/colgrep_mcp/config.py:24` (finding 6, confirmed clean)

## Evidence

**Check 1 — `cz check --message` probe table** (run from `server/`, `uv run cz check --message "<subject>"`):

| Subject | Expected | Actual | Exit |
|:--|:--|:--|:--|
| `feat(search): add x` | accept | accept | 0 |
| `feat: add x` | reject (no scope) | reject | 14 |
| `chore(repo): tidy.` | reject (trailing period) | **accept** | 0 |
| `Feat(search): add x` | reject (type case) | reject | 14 |
| `feat(Search): add x` | reject (scope case) | reject | 14 |
| `release(colgrep-mcp): v0.1.1` | accept | accept | 0 |
| `feat(search)!: drop y` | accept (breaking) | accept | 0 |
| `style(server): x` | reject (not in vocabulary) | reject | 14 |

**Check 2 — bump/changelog dry-runs**:
```
$ cd server && uv run cz bump --dry-run --increment PATCH
release(colgrep-mcp): v0.1.1 / increment detected: PATCH
## v0.1.1 (2026-09-12)
### Fixed
- **plugin**: launch the server with uv run from every manifest so it works without a POSIX shell
## v0.1.0 (2026-09-12)   <- Added / Changed / Fixed sections present, matches Keep-a-Changelog headings mapping
```
Auto-detect probe (temporary empty commits, reverted with `git reset --soft HEAD~1`, `git status` clean before and after):
```
$ git commit --allow-empty -m "feat(search)!: drop y"
$ uv run cz bump --dry-run     # no --increment: auto-detect
release(colgrep-mcp): v0.2.0 / increment detected: MINOR      <- should be MAJOR

$ git reset --soft HEAD~1   # temp commit removed
$ git commit --allow-empty -m "feat(search): drop y" -m "BREAKING CHANGE: removes the old argument shape"
$ uv run cz bump --dry-run
release(colgrep-mcp): v1.0.0 / increment detected: MAJOR      <- footer path works correctly
$ git reset --soft HEAD~1   # temp commit removed; git status clean confirmed after both
```
Source read confirming the mechanism, `.venv/lib/python3.12/site-packages/commitizen/bump.py:36-46` (`find_increment`): `found_keyword = result.group(1)` then `re.match(match_pattern, found_keyword)` against each `bump_map` key — `found_keyword` is only ever `feat`/`fix`/`perf`/`BREAKING CHANGE`, never containing `!`, so `"^.+!$"` cannot match.

Also confirmed via `.venv/.../commitizen/bump.py:83-93` (`update_version_in_files`): for `version_files` entries, only lines matching the given pattern get `current_version` string-replaced — the mechanism the leaf asked to check for `$schema` collisions (finding 6).

**Check 3 — launch consistency**: `.claude-plugin/mcp.json` and `mcp.json` both launch `uv run --quiet --directory <ROOT>/server colgrep-mcp` with a bare `uv` in `command` (verified via `test_mcp_configs_equivalent` and direct read); root `.mcp.json` is deleted, no leftover `launch.sh`/`.mcp.json`/`CLAUDE_PLUGIN_ROOT` references outside `__reports__/`/`__roadmap__/` (`git grep -n` for all three, filtered) except the intentional ones in `.claude-plugin/mcp.json`, `README.md:142`, and the explanatory comments in `test_manifests.py`.

**Check 4 — version resolution and resync**:
```
$ cd server && uv run python -c "import colgrep_mcp, importlib.metadata as m; print(colgrep_mcp.__version__, m.version('colgrep-mcp'))"
0.1.0 0.1.0
```
Non-destructive resync probe (pyproject backed up to a tempfile, `uv.lock` restored with `git checkout --` afterward, `git status` clean at the end):
```
$ sed -i.orig 's/version = "0.1.0"/version = "9.9.9"/' pyproject.toml
$ uv run python -c "..."
   Building colgrep-mcp @ file://.../server
   Uninstalled 1 package in 0.62ms / Installed 1 package in 1ms
module: 9.9.9 metadata: 9.9.9
```
`uv run` alone **did** pick up the pyproject change and reinstalled the editable package before running — it did not lag one release behind. This contradicts the documented Risk 5 mitigation and CONTRIBUTING.md's claim that "`uv run` alone does not refresh the installed editable metadata after a version bump." (Not filed as a numbered finding above because it is good news, not risk — see Hand-off Questions.)

**Check 5 — README vs manifests**: `claude mcp add colgrep -- uv run --quiet --directory /path/to/colgrep-mcp/server colgrep-mcp` matches the shape `claude mcp add [options] <name> <commandOrUrl> [args...]` from `claude mcp add --help`'s own example (`claude mcp add my-server -- my-command --some-flag arg1`) — valid.

## Re-observation Steps

1. `cd server && uv run cz check --message "chore(repo): tidy."` → should reject once `schema_pattern` is anchored; currently exits 0.
2. `git commit --allow-empty -m "feat(x)!: y" && cd server && uv run cz bump --dry-run` (no `--increment`) → currently reports `MINOR`; revert with `git reset --soft HEAD~1`.
3. `cd server && uv run cz bump --dry-run --changelog` and diff its heading style against `CHANGELOG.md`'s existing `## [x.y.z] - date` headings.
4. `diff <(jq .mcpServers.colgrep.env .claude-plugin/mcp.json) <(jq .mcpServers.colgrep.env mcp.json)` — shows the `COLGREP_MCP_ROOT` asymmetry; `cd server && uv run pytest tests/test_manifests.py -k equivalent -q` still passes despite it.
5. `grep -n "untested there\|true on Windows" README.md`.

## Hand-off Questions

Working theory: none of these are launch- or version-machinery-breaking today (pytest, ruff, and the core `cz check`/`cz bump` gates all pass); they're gaps between what the contracts *promise* and what the regexes/tests actually *enforce*, the kind of drift that surfaces later as a confusing release rather than a broken one.

1. Finding 1: should `schema_pattern` gain a `$` anchor (and arguably an explicit `[^.]$`-style rejection of a trailing period), or is "no trailing period" meant to stay a style convention that `cz check` doesn't enforce?
2. Finding 2: is the `!` shorthand meant to be a real alternate spelling of a breaking change (in which case `bump_pattern`/`bump_map` need fixing so `!` is actually captured and matched), or should CONTRIBUTING.md/the `schema` example stop advertising `!?` as meaningful for versioning purposes since only the footer counts today?
3. Finding 3: is the changelog heading style mismatch (`## v0.1.1 (date)` vs `## [0.1.0] - date`) acceptable, or does `[tool.commitizen]` need a custom changelog template to match the existing convention?
4. Finding 4: is omitting `COLGREP_MCP_ROOT` from the Agent Plugins 1.0 `mcp.json` intentional (those clients are expected to rely on MCP "roots" instead), and if so should `test_mcp_configs_equivalent` assert that difference explicitly rather than being silent about it?
5. Finding 5: should README.md's Packaging section soften "this is true on Windows" until the `ci_workflow` leaf actually runs Windows CI, to avoid contradicting its own Troubleshooting hedge?

## Scope Boundary

Read-only reviewer pass; no files outside `__reports__/repo_health/` were modified by this leaf (temporary probe commits and a temporary `pyproject.toml`/`uv.lock` edit were made and fully reverted during the session; `git status` was verified clean before writing this report and again before committing it). No fixes were applied. Any remediation for the six findings above is routed through `__roadmap__/repo_health/integrate/release/cleanup_and_release.md`, not this leaf.

## Notices

- `server/tests/test_version.py::test_manifests_match_pyproject` and `server/tests/test_manifests.py::test_versions_aligned` both assert the same three manifests' version against the pyproject source of truth. This is deliberate duplication from the file-disjoint ownership split (Risk 4: `python_tooling` owns `test_version.py`, `launcher` owns `test_manifests.py`) rather than an oversight — flagging only as a candidate for a later de-duplication pass, non-blocking.
- `test_mcp_configs_equivalent`'s `FORBIDDEN_MCP_ENV_KEYS` loop only iterates `agent_server`'s env keys, never `claude_server`'s; today `claude_server`'s env keys (`UV_PROJECT_ENVIRONMENT`, `COLGREP_MCP_ROOT`) don't collide with `{PLUGIN_ROOT, PLUGIN_DATA}` anyway, but the asymmetric check would miss it if that changed.
- The Codex `${CLAUDE_PLUGIN_ROOT}`-expansion open question from `00-findings_launch_placeholders_v0.md` (§Pointers) is still unresolved and still out of this leaf's scope; nothing in this diff changes that status.
