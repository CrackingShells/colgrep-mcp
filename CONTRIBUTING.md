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

`BREAKING CHANGE:` footer → major bump (tool renamed/removed, argument semantics changed).

### Scopes

Pick the most specific topic. Current vocabulary (extend deliberately, keep kebab-case):

`adapter` `search` `index` `resources` `prompts` `server` `plugin` `skill` `roadmap` `reports` `repo` `deps` `tests` `docs`

### Rules

- Imperative mood, lowercase after the colon, no trailing period, subject ≤ 72 chars.
- Strongly favour a body. A subject-only commit is for trivial, self-evident changes.
- One roadmap step = one commit. The step's `**Commit**` field is the subject line.
- Never commit secrets (`.env`, tokens, private keys).

### Versioning and changelog

Single-versioned package (`server/pyproject.toml` is the source of truth; plugin manifests mirror it).
`CHANGELOG.md` is hand-maintained under *Keep a Changelog* headings, one entry per `feat`/`fix`/`perf`/breaking commit, written at release time. Automation (commitizen / python-semantic-release) is deferred until there is an external consumer who reads the changelog.

## Branching

- `main` — integration target, always installable.
- `milestone/<campaign>` — one per roadmap campaign.
- `task/<leaf>` — one per roadmap leaf, branched from the milestone, rebased onto it, merged with `--no-ff`.

Agents working in parallel use git worktrees; a worktree is removed only after its branch has been merged.
