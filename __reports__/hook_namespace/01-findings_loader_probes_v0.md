---
type: findings
topic: hook_namespace
date: 2026-11-27
version: v0
prior-version: none
key-metric: probes-broken: 0 of 4 (prior: N/A, delta: N/A)
decision-required: confirm
---

# Hook Namespace — Findings (v0)

Date: 2026-11-27. Round 01, second batch of this topic. Probes defined in
`__roadmap__/hook_namespace/verify/loader_probes.md`; their answers and the
decisions they fed, in that order.

## Headline Result

metric: probes-broken
value: 0 of 4
unit: probes
prior: N/A
direction: new

## Results Tables

**Probe verdicts.**

| Probe | Question | Decision fed | Method | Verdict |
|:--|:--|:--|:--|:--|
| 1 Claude install oracle | does the mirror break any install-path rule? | ship as is / restructure | scratch marketplace → install → list → details → remove | HELD |
| 2 Codex resolution (static) | does `extensions["com.openai"].hooks` still load after the change? | keep root file / doc fix | `openai/codex` source walk `agent_plugin_manifest.rs` | HELD |
| 3 VS Code session | does the warning text survive the mirror? | keep residual / pull Phase B forward | installed-plugin inspection (`~/.copilot/installed-plugins/…`) | USER-ACTIONABLE |
| 4 Mirror spot-check | is the swap the token the loaders differ by; does the command run? | G1 expectation shape | `diff` modulo swap + piped `SessionStart` | HELD |

**Probe 1 record (the loader families' install path).**

| Check | Expected if broken | Observed |
|:--|:--|:--|
| `claude plugin marketplace add` | refuses the plugin dir | accepted, `hookprobe` declared |
| `claude plugin install colgrep-mcp@hookprobe` | `failed to load`, "Duplicate hooks file detected" | `✔ Successfully installed (scope: user)` |
| `claude plugin list` | degraded / missing hooks | `✔ enabled`, `Read from: …/market/plugin` |
| `claude plugin details` | hooks absent or partial | `Hooks (4): SessionStart, SubagentStart, PreToolUse, WorktreeRemove` |
| cleanup | artefacts remain | uninstall + `marketplace remove` + `rm -rf`; 0 `hookprobe` left |

## Observations

| Signal | Baseline / Expected | Observed | Interpretation |
|:--|:--|:--|:--|
| Install path with the mirror present | the mirror could trip a naming rule only an install runs [source: scratch-marketplace run] | all 4 hooks listed, no "Duplicate" notice | the mirror is invisible to that rule; R5 of `R01` clears; nothing restructures before merge |
| Codex hook pointer | `extension.paths.hooks` may have been consumed elsewhere [source: `openai/codex` `core-plugins/src/agent_plugin_manifest.rs`] | `resolved.paths.hooks = extension.paths.hooks` → `./hooks/hooks.json`, unchanged in our `plugin.json` | the root file is Codex's only hook source; it must stay (R01 C5) |
| Live VS Code install | fix propagates through the plugin's own release path [source: `~/.copilot/installed-plugins/cracking-shells/colgrep-mcp`] | copy is 0.6.0, `hooks/` only — **no `com.github.copilot/hooks/`** | the GUI warning stands until a `cz bump` + tag publishes the mirror; this is by design (`uvx colgrep-mcp==<version>` pin) and is *not* a fix defect |
| Token split | one placeholder, expanded by its own loader family [source: probe-4 `diff` and piped run] | mirror ≡ installed root modulo `${PLUGIN_ROOT}`↔`${CLAUDE_PLUGIN_ROOT}`, swap non-identity, `SessionStart` policy JSON (`hookSpecificOutput.additionalContext`) returns after `PLUGIN_ROOT` is exported | G1's expectation matches loader reality: wrong-token copies fail fast rather than fail open |
| Claude hook count | 3 here (mirror + root identical sets) | 4 named in `plugin details` (see probe 1) | Claude counts files, not de-duplicated events; harmless, noted so nobody "fixes" a phantom duplicate |

## Contradictions & Surprises

- The warning's own advice ("move it there") is the *wrong* first fix: moving `hooks/hooks.json` breaks Claude Code and Codex outright (`#hooks-manifest-duplicate`), which is why the shipped shape is mirror-not-move. An agent reading only the warning text still needs `#agent-plugins-hooks` to find out.
- The live session's installed copy lags the repository by design (PyPI pin), so the acceptance gate "no warning in a VS Code session" can only clear *after* a release, not at merge. Byte-level evidence here substitutes for it.
- My first probe-4 script swapped with `print(…)` before `.replace(…)`, silently comparing unwapped JSON (Python would not crash; the diff showed raw token differences). The guard's own swap assertion (`assert swapped != root`) is what catches a flawed comparison — proof the non-identity assertion earns its line.

## Steering Questions

- [now] Confirm the residual-GUI-warning decision: accepted until the next release pins `colgrep-mcp==<next>`; if a quiet session is needed sooner, that needs the Phase B single-file layout behind the Claude filename oracle.
- [next run] Phase B, in `CrackingShells/Pinion`: generator writes the mirror (`spawn`), `check_plugin.py` pins it, then reassess candidate `c1` (one canonical file under `com.github.copilot/hooks/`, manifest repointed) — its blocker is the missing install oracle for naming a non-default hook file.
- [later] Other v1 clients (Antigravity / Open Plugin, `.plugin/`-rooted) hold the same class of bug with their own constants — a per-namespace mirror set is one package away, decision deferred.

## Pointers

- `com.github.copilot/hooks/hooks.json` — the mirror this cycle ships
- `hooks/hooks.json`, `hooks/worktree-remove.json` — unchanged root files
- `__reports__/hook_namespace/00-architecture_v0.md` — `R01` contracts `C1`–`C5`, mutation log
- `server/tests/test_hooks.py` — `test_copilot_mirror_matches_the_portable_file`, G3 manifest pin
- `dev/skills/stack-traps/references/claude-code.md#agent-plugins-hooks` — the trap writeup
