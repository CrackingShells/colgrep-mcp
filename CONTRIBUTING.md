# Contributing

## Commit convention

This repository uses Conventional Commits with a **mandatory scope**:

```
type(scope): description

[body: WHY the change exists — context, constraints, trade-offs]

[footers]
```

### Allowed types

| Type | Bump | Use for |
|:-----|:-----|:--------|
| `feat` | minor | New server capability visible to an MCP client (tool, resource, prompt, completion) or new plugin surface |
| `fix` | patch | Corrects behaviour that contradicts the architecture report or a test |
| `refactor` | none | Restructures without changing observable behaviour |
| `perf` | patch | Latency / token-cost improvement with a measured before/after |
| `test` | none | Adds or changes tests only |
| `docs` | none | Reports, roadmap, README, SKILL.md prose, docstrings |
| `build` | none | pyproject, uv lock, packaging, plugin manifests |
| `chore` | none | Repo housekeeping that fits nowhere else |
| `release` | — | Bump commits only, written by `cz bump`. Never author one by hand. |

`BREAKING CHANGE:` footer → major bump (tool renamed/removed, argument semantics changed).

### Scopes

Pick the most specific topic. Current vocabulary (extend deliberately, keep kebab-case):

`adapter` `search` `index` `resources` `prompts` `server` `plugin` `skill` `roadmap` `reports` `repo` `deps` `tests` `docs`

### Rules

- Imperative mood, lowercase after the colon, no trailing period, subject ≤ 100 chars (the whole line, prefix included; `cz check` enforces it).
- Strongly favour a body. A subject-only commit is for trivial, self-evident changes.
- One roadmap step = one commit. The step's `**Commit**` field is the subject line.
- Never commit secrets (`.env`, tokens, private keys).

### Versioning and changelog

Single-versioned package: `server/pyproject.toml` `[project].version` is the **only** place a
human or agent edits a version, and even that only through `cz bump` — never hand-edit it.
`colgrep_mcp.__version__` is derived at import time from installed package metadata
(`importlib.metadata.version("colgrep-mcp")`); it is never a literal to keep in sync by hand.

The commit vocabulary above is encoded as [Commitizen](https://commitizen-tools.github.io/commitizen/)
machinery in `server/pyproject.toml`'s `[tool.commitizen]` / `[tool.commitizen.customize]`
tables — the tables are the enforcement, this prose is only a description of them. Run every
`cz` command from `server/`, same as every other tool in this repo.

`cz bump` (run from `server/`) is the only thing that rewrites a version: it bumps
`pyproject.toml`, `uv.lock` (re-locked by a `pre_bump_hooks` entry), the three plugin manifests
(`plugin.json`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, via `version_files`), appends to `../CHANGELOG.md` under the
matching *Keep a Changelog* heading (`feat`→Added, `fix`→Fixed, `perf`→Changed), and tags
`v<version>`. It writes its own `release(colgrep-mcp): v<new_version>` commit — do not author
that commit by hand.

The release recipe is:

```
cd server
uv run cz bump --changelog
uv run pytest   # uv run re-syncs the editable install, so __version__ already reports the new version
```

### Checks

Gate commands, run from `server/`:

- `uv run pytest` — the test suite, including the version-drift guards in
  `tests/test_version.py`, `tests/test_manifests.py` and `tests/test_changelog.py`.
- `uv run ruff check` — lint; clean is the norm, not aspirational.
- `uv run cz check --rev-range main..HEAD` — validates every commit on the branch against the
  vocabulary above.

Enforcement is **advisory locally, mandatory in CI**: there is no git commit hook (agents
author commits directly; a blocking hook costs a retry loop for no local benefit). CI runs
`cz check` over the pull request's commit range, and a failing gate blocks merge there.

## Branching

- `main` — integration target, always installable.
- `milestone/<campaign>` — one per roadmap campaign.
- `task/<leaf>` — one per roadmap leaf, branched from the milestone, rebased onto it, merged with `--no-ff`.

Agents working in parallel use git worktrees; a worktree is removed only after its branch has been merged.
