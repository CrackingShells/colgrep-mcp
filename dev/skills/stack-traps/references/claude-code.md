# Claude Code plugin loader traps

## A freshly opened repo shows a pending colgrep entry or `spawn ENOENT` {#root-mcp-json}

**Symptom**: opening this repository (or a clone of it) as a plain project
in Claude Code shows a second, pending `colgrep` MCP entry, or a
`spawn '${CLAUDE_PLUGIN_ROOT}/...'` / `posix_spawn` ENOENT error, even
though the plugin itself connects fine when loaded as a plugin.

**Cause**: a root-level `.mcp.json` is read by Claude Code as *project*
scope MCP config — a completely different loading path from the plugin
loader, one that has no notion of `CLAUDE_PLUGIN_ROOT` and so leaves the
placeholder unexpanded, tried literally as a path. This is why this
repository's MCP config lives at `.claude-plugin/mcp.json` instead: a
root-level project open then discovers no `mcpServers.colgrep` entry at
all. No manifest carries a placeholder in `args` — every one launches
`uvx colgrep-mcp==<version>` (see `#uvx-pin`) — and the only placeholder at
all, `COLGREP_MCP_ROOT=${CLAUDE_PROJECT_DIR}` in `env`, is in the Claude Code
manifest only; Codex has its own `.codex-plugin/mcp.json` without it.
Placeholders belong only in `args`/`env` (never `command` — no ecosystem
expands placeholders there); `${VAR:-default}` fallback syntax is documented
only for *project*-scope `.mcp.json`, not for the plugin substitution path,
so don't rely on it there. Agent Plugins 1.0 goes further and forbids any
fallback syntax outright — "unrecognized placeholder-like text MUST remain
literal." (`PH`, pypi_publication R01 §C6.)

**What to do**: never add or restore a root-level `.mcp.json` to this
repository. If a manifest needs to reference the server config, point it at
`.claude-plugin/mcp.json`. If you need a fallback value in a plugin-scope
manifest, don't assume `${VAR:-default}` works — treat it as unverified and
either hardcode or make the field required.

## The plugin connects but runs the PyPI release, not your tree {#uvx-pin}

**Symptom**: `claude --plugin-dir . mcp list` shows `✔ Connected` while an
edit you just made is not in the running server; or, right after a `cz
bump`, the plugin fails to start with a uv resolution error naming a
version; or, in the minutes *after* `publish.yml` went green, the plugin
shows `✘ Failed to connect — CONNECTION_CLOSED` although
`uvx --no-cache colgrep-mcp==<version> --version` works.

**Cause**: every MCP manifest launches `uvx colgrep-mcp==<version>` from
PyPI, pinned to the plugin's version; the plugin loader never runs the
checkout's code. The pin is a `version_files` target, so between the bump
commit and a successful `publish.yml` run it names a version PyPI does not
have yet — by design, so that a plugin update can never reuse a stale
cached environment (pypi_publication R01 §C6, D4).

The third symptom is uv's HTTP cache: it keeps PyPI's simple-index page for
`colgrep-mcp` for as long as PyPI's cache headers allow, so a pin that was
uploaded a moment ago is "no version of colgrep-mcp==X" to a warm cache.
The plugin loader shows none of that text — only the closed pipe.

**What to do**: after a release, warm the cache once with
`uvx --refresh colgrep-mcp==<version> --version`, then re-run the gate. To
exercise the tree, register it directly —
`claude mcp add colgrep-dev -- uv run --quiet --directory ./server
colgrep-mcp` — and read `claude --plugin-dir . mcp list` only as "the
manifest is well-formed". After a bump, wait for `publish.yml` to go green
(re-run it from the Actions tab if the upload failed); never edit the pin by
hand and never re-tag.

## The install/list command reads oddly or fails to resolve {#namespaces}

**Symptom**: `claude plugin install colgrep-mcp@cracking-shells` names a
marketplace that is not the repository; an install string copied from an
older README or report (`colgrep-mcp@colgrep-mcp`,
`colgrep-mcp@colgrep-mcp-marketplace`) no longer resolves; or an install
command copied from Claude Code's convention doesn't work verbatim for
Codex.

**Cause**: marketplace names and plugin names live in separate namespaces,
`<plugin>@<marketplace>`. Both marketplace files
(`.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`) name
themselves `cracking-shells`, the organization, so one marketplace can carry
every CrackingShells plugin; the plugin keeps the repository's name. Until
after v0.5.0 the Claude marketplace was named `colgrep-mcp` and the Codex one
`colgrep-mcp-marketplace`, so reports and machines from that period still
carry those strings, and a machine that added the marketplace under the old
name keeps it under that name until it is removed and re-added. A `source`
field of `"./"` or `"./dev"` in a marketplace manifest resolves relative to
the marketplace root, which works for a marketplace added from a git source
or local directory but not for a direct URL to the `marketplace.json` file
itself. (`RI`.)

**What to do**: on a machine that shows `colgrep-mcp` under
`claude plugin marketplace list`, run
`claude plugin marketplace remove colgrep-mcp` and add it again, then
reinstall `colgrep-mcp@cracking-shells`. When writing install instructions
for a second ecosystem, copy that ecosystem's own marketplace `name`; here
the two happen to match, which is a choice, not a rule.

## `claude -p` / `claude plugin eval` fails with an OAuth error {#oauth}

**Symptom**: `claude -p` fails with something like `Failed to authenticate:
OAuth session expired`; `claude plugin eval` or skill-creator's
`run_loop.py`/`run_eval.py` fail the same way.

**Cause**: all of these need an authenticated `claude -p` session; when
the OAuth session has expired, none of them has a working fallback.
(`KT-B`.)

**What to do**: don't treat this as a bug in the plugin or the skill.
Degrade the plugin-connectivity gate to `claude --plugin-dir . mcp list`
(non-interactive, shows `✔ Connected` without needing `-p`) instead of
trying to force `claude -p` to work. The eval cases in
`dev/evals/*/case.yaml` need the same authenticated session; run them from
one that has it.

## The plugin's hooks don't fire, or run the old text, after a change {#plugin-hooks}

**Symptom**: you edited `hooks/hooks.json` or `hooks/colgrep_policy.py`
(or a plugin update just landed) and a `grep -r` still passes, the
session-start policy is the old one, or `/hooks` lists nothing under
Plugin Hooks; in Codex the hooks are listed but never run.

**Cause**: plugin hooks are read when the plugin is loaded, not per call.
Claude Code needs `/reload-plugins` or a new session, and a
marketplace-installed plugin runs the *cached* copy under
`~/.claude/plugins/cache/`, not your tree; `claude --plugin-dir .` loads
the tree's hooks — and, unlike the MCP manifest (`#uvx-pin`), they really
do run from the tree, because they are scripts, not a PyPI pin. Codex
skips plugin-bundled hooks until you review and trust them in `/hooks`,
and marks them for review again whenever the hook definition's hash
changes. Cursor loads Claude Code hooks only from `settings.json` files,
never from a plugin. (harness_wiring R01 risk 7, D8.)

**What to do**: after editing, `/reload-plugins` (or restart) in Claude
Code; in Codex open `/hooks` and trust; for Cursor copy the three
`hooks.json` entries into the project's `.claude/settings.json`. Test the
script without any harness by piping it the event JSON —
`server/tests/test_hooks.py` does exactly that through `sys.executable`,
so `uv run pytest tests/test_hooks.py` is the fastest check. Keep
Claude-only events (`WorktreeRemove`) in `hooks/claude-code.json`, never in
the portable `hooks/hooks.json` a Codex parser also reads, and name only
`claude-code.json` from the Claude Code manifest (`#hooks-manifest-duplicate`);
`test_hooks.py` pins the split.

## `claude plugin list` says "failed to load: Duplicate hooks file detected" {#hooks-manifest-duplicate}

**Symptom**: after `claude plugin install` or `claude plugin update`, the
plugin shows `✘ failed to load` with `Hook load failed: Duplicate hooks file
detected: ./hooks/hooks.json resolves to already-loaded file
~/.claude/plugins/cache/<marketplace>/colgrep-mcp/<version>/hooks/hooks.json`,
and nothing of the plugin — hooks, MCP server, skill — is available; yet
`claude --plugin-dir . plugin details colgrep-mcp` on the very same tree lists
all four hooks and `claude plugin validate .` passes.

**Cause**: Claude Code loads `hooks/hooks.json` automatically and reads the
manifest's `hooks` field as *additional* files only (the plugins reference
documents the field with the example `"./my-extra-hooks.json"` and files
hooks under "own merge rules"; the error text states the rule outright). A
manifest listing `./hooks/hooks.json` names the default twice, and the
marketplace loader refuses the whole plugin — observed with Claude Code
2.1.270 on the 0.4.0 and 0.5.0 installs. Neither `--plugin-dir`, `plugin
details` nor `plugin validate` runs that check, so every tree-level gate in
`AGENTS.md` stayed green on a manifest the install path rejected. harness_wiring
R01 §C2 designed the manifest as an array of both files before the rule was
documented; the manifest carried it from 0.4.0 until this fix.

**What to do**: the Claude Code manifest's `hooks` is the single string
`"./hooks/claude-code.json"`; never add `./hooks/hooks.json` back —
`test_hooks.py::test_manifests_name_the_hook_files_per_ecosystem` pins it, and
the Codex manifest keeps naming `./hooks/hooks.json` because Codex has no
auto-load documented (R01 risk 1). To check a manifest the way an install
does, register a scratch directory marketplace (a `marketplace.json` with a
throwaway `name` whose plugin `source` is a copy of the tree without `.git`
and `.venv`), `claude plugin install colgrep-mcp@<that-name>`, read
`claude plugin list`, then uninstall and `claude plugin marketplace remove` it.
`--plugin-dir` is not that check.

## An implementer's worktree is based on `main`, not the campaign branch {#agent-worktree}

**Symptom**: an implementer dispatched with the Agent tool reports "leaf file
missing" in its first minute, or its commits turn out to sit on a branch cut
from `main` while the roadmap, specs and helpers live on the campaign branch.

**Cause**: the Agent tool's `isolation: "worktree"` option creates the
worktree from the primary checkout's HEAD — `main` — never from the branch
the lead's session is on. One whole dispatch round landed on the wrong base
this way (`KT-H` §Pain Points, `KT-B` §Root Causes). This is the Claude Code
instance of the harness-neutral rule in `campaign-lead` step 4.

**What to do**: create every implementer worktree yourself, `git worktree
add <path> -b task/<leaf> <campaign-branch>`, and pass the path in the
dispatch prompt; never set `isolation: "worktree"` from a campaign branch.
Keep the "stop if the leaf file is missing" line in every prompt — it is what
turned the wrong-base round into a 15-second no-op.

## A subagent said it was watching CI, and nothing happened {#worker-turn}

**Symptom**: an implementer's final message says it is "watching CI in the
background" or "will follow up when the run finishes"; the run finishes red
or green and nothing follows.

**Cause**: an Agent-tool subagent's turn ends with its final message; there
is no later execution, so any promise about the future in that message is
never kept. The same holds for any harness whose workers return a single
report (`campaign-lead` §Rules).

**What to do**: make the implementer block inside its turn — `gh run watch
--exit-status <run-id>` — and paste the verdict line into its report, or read
the run yourself after the report. Never treat a worker's "watching" as a
gate result.
