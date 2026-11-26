# Mirror and Guards

**Goal**: Ship `com.github.copilot/hooks/hooks.json` — the portable policy mirrored for Agent Plugins v1 loaders — with one guard per behavior, each naming the plausible bug it catches and each seen red once.
**Pre-conditions**:
- [ ] `__reports__/hook_namespace/00-architecture_v0.md` is committed, being the `R01` contracts this leaf encodes
- [ ] `cd server && uv run pytest -q` is green on the task branch before the change
**Success Gates**:
- ✅ Each guard below was run red on its named bug before it passed, and the red runs are named in the commit body [run]
- ✅ `cd server && uv run pytest tests/test_hooks.py -q` passes with `test_copilot_mirror_matches_the_portable_file` among the cases [run]
- ✅ `git show --stat` on the leaf's commit lists only `com.github.copilot/hooks/hooks.json` and `server/tests/test_hooks.py` [run]
**References**: [R01 §Contracts](../../__reports__/hook_namespace/00-architecture_v0.md) — the token-per-loader rule and the per-event pin this leaf encodes

## Step 1: Mirror the portable hooks under the reverse-DNS directory
**Goal**: Make the Copilot/VS Code loader find the same three policy events Claude Code and Codex find at the root, under the two guards that each catch a bug the other cannot.
**Implementation Logic**:
Guards first, mirror second, one commit (maintainer-policy: a regression test must have failed once; the body lists each red run).
1. `test_copilot_mirror_matches_the_portable_file` — **behaviour**: the mirror's `hooks` block equals `hooks/hooks.json`'s with `${CLAUDE_PLUGIN_ROOT}` swapped for `${PLUGIN_ROOT}`. **Scope**: the two real hook files, the only artefacts the two loader families read (consumer: any loader, plus the maintainer who edits one copy). **Named bug (G1)**: policy divergence between the copies — a dropped event, or a changed `matcher`, `timeout` or `statusMessage` in one file only. Derive the expected value from the root file and **assert the swap actually changed it**, so a no-op substitution cannot make the comparison always true. Injection: delete `PreToolUse` from the mirror → red; restore.
2. In `test_manifests_name_the_hook_files_per_ecosystem`, assert `plugin.json`'s `extensions` carries no `com.github.copilot` key — **scope**: the manifest the v1 loader consults before the default path (consumer: the loader's own manifest resolution). **Named bug (G3)**: an `extensions["com.github.copilot"].hooks` path config with `exclusive: true` silently disclaims the default directory (VS Code `parseComponentPathConfig`), reintroducing today's bug through the one manifest route that bypasses the file. Injection: add such a key → red; remove it. A third candidate — extending `test_every_handler_launches_the_one_script_through_the_one_launcher` to the mirror — was mutation-checked and cut as tautological (G1's equality plus the existing root sweep already imply every per-command property); the rationale is recorded in `R01` §Alternatives, so do not add it back as "coverage".
Then land `com.github.copilot/hooks/hooks.json`: groups `SessionStart`, `SubagentStart`, `PreToolUse` (`matcher: "Grep|Bash"`), each command `uv run --no-project --quiet python "${PLUGIN_ROOT}/hooks/colgrep_policy.py"` with the root file's `timeout` and `statusMessage`. No `WorktreeRemove` mirror and no manifest key: the v1 loader finds the file by path and `WorktreeRemove` is Claude Code's alone. The mirror's own `description` may name the v1 reader — only the `hooks` block is pinned equal. Not tested here by design: loader-parser internals (observed, not owned), Codex's runtime (probe in `verify/`), schema conformance of keys we do not add (already pinned by `test_manifests_name_the_hook_files_per_ecosystem`'s whitelist assertions).
**Deliverables**: `com.github.copilot/hooks/hooks.json` — hook groups `SessionStart`, `SubagentStart`, `PreToolUse`; `server/tests/test_hooks.py` — `COPILOT_MIRROR`, `test_copilot_mirror_matches_the_portable_file`, extended `test_manifests_name_the_hook_files_per_ecosystem`
**Consistency Checks**: `cd server && uv run pytest tests/test_hooks.py -q` (expected: PASS)
**Commit**: `fix(hooks): mirror the portable hooks under com.github.copilot`
