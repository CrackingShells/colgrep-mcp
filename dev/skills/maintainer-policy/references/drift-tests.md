# Drift tests: what each guard pins, and how to add one

A drift test exists because two (or more) artefacts that must always agree
are maintained by hand, by different commits, sometimes by different
agents — a version number written in five places, a table in a README that
must match the tools a server actually ships. Nothing stops them drifting
apart except a test that fails the moment they disagree. See `../SKILL.md`
§Drift tests, not checklists for why this is preferred over a checklist item
in a leaf or a PR template.

## The existing guards

| Test file | What it pins |
|:--|:--|
| `tests/test_version.py` | `colgrep_mcp.__version__` equals `pyproject.toml`'s version; every manifest's `version` field equals it too; `uv.lock` records exactly that version for this package. |
| `tests/test_manifests.py` | All four plugin manifests (`plugin.json`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `dev/.claude-plugin/plugin.json`) carry the same version; the Agent Plugins 1.0 manifest only uses its permitted field set and the right `$schema`; the three ecosystems' MCP server configs launch the server the same way (same `uv run` invocation shape, no unexpanded `$` placeholders outside project scope). |
| `tests/test_changelog.py` | Every `## ` version heading in `CHANGELOG.md` is shaped so commitizen's incremental changelog mode can parse it — a hand-written Keep-a-Changelog heading in the wrong shape would make `cz bump --changelog` duplicate that section instead of appending to it. |
| `tests/test_readme.py` | The tool names listed in the Tools table of `README.md` and of `server/README.md` (the PyPI page) match the tools the server actually registers — a renamed or removed tool that isn't updated in a README fails here instead of shipping stale docs. |
| `tests/test_packaging.py` | `server/LICENSE` is a byte copy of the repository `LICENSE` (hatchling only packages files under `server/`); `[project.urls]` point at the repository; no tracked text file carries a path from a maintainer's machine. |
| `tests/test_hooks.py` | The hook script's decisions for each event, fed the harness's JSON by hand; `hooks/hooks.json` carries only events every hook-capable harness knows and every other file exactly one event, named after it (`hooks/worktree-remove.json`); the Claude Code manifest names only the extra files (it auto-loads `hooks.json`), the Codex manifest only the portable one (its field replaces default discovery). |
| `tests/test_dev_plugin.py` | `AGENTS.md` stays under its line cap and names every skill under `dev/skills/`; every `dev/skills/*/SKILL.md` has front matter whose `name` matches its directory and a description long enough to state when to load it; the dev plugin manifest is the versioned skills plugin (no `mcpServers`); the marketplace lists both plugins from disjoint sources; the product plugin's skills path never resolves inside `dev/`. |

## Recipe for a new one

1. **Name the two artefacts and the disagreement that would hurt.** A drift
   test is only worth writing when an actual future edit could plausibly
   update one side and not the other — not for artefacts that are already
   generated from a single source.
2. **If a generator produces one side** (a bump tool, a scaffold script, a
   template renderer), run it in dry-run mode against the artefact that
   already exists in the repository first, and diff the result against what
   is actually committed. Accepting a generator's config without this step is
   how a drift guard itself drifts — the guard ends up pinning what the
   generator *would* produce today, not what the repository actually needs
   tomorrow.
3. **Pin the parseable shape, not the full content.** `test_changelog.py` is
   the model: it doesn't assert the changelog's prose is correct, it asserts
   the heading shape is one commitizen's parser can consume. A drift test
   should fail on the structural mismatch that would actually break tooling,
   not on every cosmetic edit to the artefact.
4. **Put it in `server/tests/` next to its siblings** and add it to the table
   above in this file the next time this skill is touched, so the inventory
   stays a checklist an agent can trust rather than needing to re-derive it
   from source.
