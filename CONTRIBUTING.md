# Contributing

This repository is maintained by LLM agents. The process knowledge lives in the
`colgrep-mcp-dev` plugin (`claude --plugin-dir ./dev`); see `AGENTS.md`. This
file keeps only what the commitizen machinery in `server/pyproject.toml`
enforces, so that the prose and the enforcement cannot disagree for long.

## Commit convention

Conventional Commits with a **mandatory scope**: `type(scope): description`,
imperative, lowercase after the colon, no trailing period, whole subject
≤ 100 chars, then a body saying WHY. One roadmap step = one commit.

| Type | Bump | Use for |
|:-----|:-----|:--------|
| `feat` | minor | New server capability visible to an MCP client (tool, resource, prompt, completion) or new plugin surface |
| `fix` | patch | Corrects behaviour that contradicts the architecture report or a test |
| `refactor` | none | Restructures without changing observable behaviour |
| `perf` | patch | Latency / token-cost improvement with a measured before/after in the body |
| `test` | none | Adds or changes tests only |
| `docs` | none | Reports, roadmap, README, SKILL.md prose, docstrings |
| `build` | none | pyproject, uv lock, packaging, plugin manifests |
| `chore` | none | Repo housekeeping that fits nowhere else |
| `release` | — | Bump commits only, written by `cz bump`. Never author one by hand. |

`BREAKING CHANGE:` footer → major bump (tool renamed/removed, argument semantics changed).

Scopes (kebab-case, extend deliberately):
`adapter` `search` `index` `resources` `prompts` `server` `plugin` `skill` `roadmap` `reports` `repo` `deps` `tests` `docs`

## Versioning and release

`server/pyproject.toml` `[project].version` is the only version source and only
`cz bump` edits it; the manifests, `uv.lock` and `CHANGELOG.md` follow. From the
main checkout, on `main`:

```
cd server
uv run cz bump --changelog
uv run pytest
git push origin main v<new_version>   # the tag is lightweight: --follow-tags does not push it
```

Pushing the tag is the publish decision: `.github/workflows/publish.yml` builds the
distribution, uploads it to PyPI through trusted publishing (no token; the publisher
registered on PyPI names `publish.yml` and the `pypi` environment) and creates the
GitHub release from the tag's `CHANGELOG.md` section. The `uvx colgrep-mcp==<version>`
pin in the three MCP manifests is a `version_files` target, so the bump moves it too.

## Gates

From `server/`: `uv run pytest`, `uv run ruff check`, `uv run ruff format --check`,
`uv run cz check --rev-range main..HEAD`. Enforcement is advisory locally and
mandatory in CI (no commit hook). Branches: `main` always installable,
`task/<leaf>` per roadmap leaf, rebased then merged `--no-ff`.

Everything else — landing a PR, worktrees, conflict markers, commitizen
gotchas, what a reviewer checks — is the `landing-and-release` and
`campaign-lead` skills.
