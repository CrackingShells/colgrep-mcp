# repo_health — Knowledge Transfer (v0)

Date: 2026-09-12

## Executive Summary
- **What shipped**: colgrep-mcp 0.1.1 — no server behaviour change. The scaffold around it is now mechanical: `__version__` derives from package metadata; the CONTRIBUTING vocabulary is commitizen machinery (`cz check`, `cz bump` writing pyproject, three manifests and the changelog); every manifest launches `uv run --quiet --directory <ROOT>/server colgrep-mcp` and the POSIX launcher is gone; the Claude Code MCP config moved to `.claude-plugin/mcp.json` so the repo no longer auto-loads a broken server when opened as a project; `ruff check` is a clean gate; a three-OS CI workflow and `AGENTS.md` exist; 27 merged branches from the 0.1.0 campaign are deleted.
- **Primary outcomes**: ≈50 min (11:38 → ~12:25) wall time, one lead (Fable) with two Sonnet implementers and one Sonnet reviewer; 196 tests pass (193 → +2 version drift, +1 changelog drift), ruff clean, `cz check` passes over the whole history; the 0.1.1 release was cut by the machinery this campaign introduced.

## Wins
- **File-disjoint leaves by construction.** Declaring ownership per leaf in the roadmap README §Gotchas produced zero merge conflicts across two parallel branches that both touched tests and docs.
- **"Stop if the leaf file is missing" paid for itself in the first minute.** Both implementers were dispatched into worktrees created from `main` instead of the campaign branch, noticed within 15–30 s, and stopped with no stray commits.
- **Machinery verified against real history, not examples.** `cz check` was run over all 79 commits before the config was accepted; `cz bump --dry-run` predicted 0.1.1 from the history alone.
- **The lead doing the mechanical glue** (branch cleanup, CI, AGENTS.md, changelog-heading fix) kept the implementers to two well-bounded leaves.

## Pain Points
- `Agent` tool `isolation: "worktree"` branches from the primary checkout's HEAD (`main`), not from the session's campaign branch — one wasted dispatch round.
- Commitizen's incremental changelog cannot parse Keep-a-Changelog headings; the hand-written `## [0.1.0] - date` would have been duplicated on the first bump. Found by the lead probing `cz changelog --dry-run --incremental`, not by any test.
- `cz bump --dry-run` does not list the files it would touch; the leaf's gate had to be replaced by `git status --porcelain` on those paths.
- The shell-search hook blocks `grep` inside heredocs that merely *mention* grep; harmless but costs a retry.
- Two confirmed defects in the commitizen config (unanchored `schema_pattern`, dead `bump_map` key for `!`) survived the implementer's own gates because `cz check --rev-range` only ever sees *valid* history; only adversarial `--message` probes exposed them.
- CONTRIBUTING's 72-character subject limit had already been exceeded by ten commits, several of them roadmap `**Commit**` subjects written by the lead.

## Root Causes
- The worktree isolation feature assumes single-branch sessions; campaign branches in a session worktree violate that assumption silently.
- Two changelog conventions coexisted (hand-written Keep-a-Changelog vs commitizen's template) with no test relating them.
- Gate wording in leaf files assumed tool output shapes that were never observed (R01 Risk 5 was about `uv sync`, not about dry-run verbosity).

## Next-cycle Changes
- **Instruction changes**: dispatch prompts name the worktree path and branch explicitly and never use `isolation: "worktree"` from a campaign branch (now in `AGENTS.md` §Coordinating a campaign and in memory).
- **Workflow changes**: before accepting any generator config (changelog, docs, manifests), run its dry-run against the *existing* artefact and diff; add a drift test for the artefact's parseable shape (done here for CHANGELOG headings).
- **Review process changes**: keep the reviewer pass, and have it probe every *validator* with a handful of deliberately invalid inputs, not only read the diff; that is where both machinery defects came from.
- **Product follow-ups**: publish to PyPI so manifests become `uvx colgrep-mcp` (and `server/README.md`, a two-line stub, becomes the PyPI page); run `ruff format` once as a standalone commit; read the Windows CI result once a remote exists (the manifests' `homepage`/`repository` URLs name a GitHub repo that does not exist yet and the `gh` account differs from the URL's owner — decide the canonical location before publishing); answer the Codex placeholder question (`.codex-plugin/plugin.json` points at `.claude-plugin/mcp.json` and Codex's expansion of `${CLAUDE_PLUGIN_ROOT}` is still unverified); consider a `${CLAUDE_PLUGIN_ROOT:-.}` request upstream so a root `.mcp.json` could serve both contexts.
- **Deferred from the review** (plausible, medium): `.claude-plugin/mcp.json` sets `COLGREP_MCP_ROOT=${CLAUDE_PROJECT_DIR}` while the Agent Plugins 1.0 `mcp.json` has no equivalent placeholder, so those clients rely on the roots/cwd fallback documented in the README; decide whether to add a spec-conformant equivalent once an Agent Plugins client is actually tested.

## Artifacts to Preserve
- `__reports__/repo_health/00-architecture_v0.md` — the contracts C1–C5; C2 is the commitizen configuration in prose.
- `__reports__/repo_health/00-findings_launch_placeholders_v0.md` — where each ecosystem expands root placeholders, with quoted spec sentences; reusable for any multi-ecosystem plugin.
- `__reports__/repo_health/01-observation_review_v0.md` — reviewer findings and the `cz check --message` probe table.
- `server/tests/test_version.py`, `test_manifests.py`, `test_changelog.py`, `test_readme.py` — the four drift guards that make the scaffold self-checking.
- `AGENTS.md` — the orientation file; keep it under ~120 lines and pointer-heavy.

## Open Questions
- Does Codex expand `${CLAUDE_PLUGIN_ROOT}` in `.claude-plugin/mcp.json`? (carried from 0.1.0)
- Does the Windows matrix job pass? Unknown until the repository has a remote.
- Should `ruff format` be adopted (one-time churn) now that no parallel branch is open?
- Should the subject-length limit stay at 100, or should roadmap `**Commit**` fields be written shorter? The machinery now enforces 100; the choice is editorial.
