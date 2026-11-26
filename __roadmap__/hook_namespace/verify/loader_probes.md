# Loader Probes

**Goal**: Answer, with each loader's own rules, the four open questions that decide whether the mirror ships as is; end with every probe marked broken or held and its decision recorded.
**Pre-conditions**:
- [ ] `mirror_and_guards` and `docs_and_naming` have reported, with gates green on the integration branch
- [ ] `claude` is on the PATH and no `hookprobe` marketplace or plugin is left from an earlier run
**Success Gates**:
- ✅ `__reports__/hook_namespace/01-observation_loader_probes_v0.md` marks every probe below broken or held, each with its reproducer or the probe that tried, and records the decision each answer fed [behavioral]
- ✅ The scratch-marketplace run installs the plugin, `claude plugin list` shows it loaded with its hooks, no "Duplicate hooks file detected" appears, and both artefacts are removed afterwards [run]
- ⬜ A Copilot/VS Code session lists the three portable hooks for colgrep-mcp (needs the user's session; a legacy root-file notice is accepted) [behavioral]
**References**: [R01 §Evidence](../../__reports__/hook_namespace/00-architecture_v0.md) — the exact claims each probe attacks

## Step 1: Run the loader probes
**Goal**: Break the shipped shape the way each loader would, or record that it holds, and record the decision each answer fed.
**Implementation Logic**:
Read-only against the tree; probe scripts live in the scratchpad, findings in the report; this leaf's single commit carries the report. Each probe is a question feeding a named decision — no probe exists without one.
1. **Claude Code install oracle. Question**: does the marketplace install still load the plugin now that a second hook file sits under `com.github.copilot/`, and does any naming rule trip? **Decision it feeds**: ship as is, or restructure before merge. Copy the tree without `.git` and `.venv` into a scratch directory holding a throwaway `.claude-plugin/marketplace.json`, then `claude plugin marketplace add <dir>`, `claude plugin install <plugin>@hookprobe`, `claude plugin list` (expect: loaded, hooks listed, no "Duplicate hooks file detected"), then uninstall plus `claude plugin marketplace remove`. This is the only oracle for the rule `plugin validate` cannot see (stack-traps `claude-code.md#hooks-manifest-duplicate`); both existing pins in `test_manifests_name_the_hook_files_per_ecosystem` must stay green untouched.
2. **Codex resolution, static. Question**: does `extensions["com.openai"].hooks: "./hooks/hooks.json"` still resolve to a loaded hooks file in Codex's sources after the change? **Decision it feeds**: whether the root file must remain (it does) and whether any Codex-facing doc line needs correcting. Walk `openai/codex` `core-plugins/src/agent_plugin_manifest.rs` (`extension.paths.hooks`) and the hooks engine's `PluginHookSource`; record that plugin hooks stay inert until a one-time `/hooks` trust and that no Codex CLI is on this machine (source-verified only, as the README states).
3. **VS Code/Copilot session. Question**: with the plugin loaded in the user's real session, does the warning "Some hook files could not be loaded" survive the mirror, do the mirror's three hooks register, and does `hooks/worktree-remove.json` claim attention under v1? **Decision it feeds**: whether the residual legacy notice is accepted as documented, or whether Phase B's single-file layout must be pulled forward. Record the notice text verbatim either way.
4. **Mirror rule spot-check. Question**: is the swap the token the two loader families actually differ by, and does the mirrored command text produce the policy? **Decision it feeds**: whether G1/G2's expectation shape matches loader reality (`diff` the two files after `${CLAUDE_PLUGIN_ROOT}` → `${PLUGIN_ROOT}`; run one `SessionStart` event through the mirrored command text with the substitution applied and expect the policy JSON back).
Probe outcomes feed the cycle close: findings go to the lead, broken probes block the merge until fixed or explicitly accepted (campaign-lead §Rules). Probes are never kept as tests — their answers live in the report; the guards in `mirror_and_guards` are what stays.
**Deliverables**: `__reports__/hook_namespace/01-observation_loader_probes_v0.md` — probe table with reproducers and per-probe decisions; scratchpad probe scripts stay outside the repo
**Consistency Checks**: `cd server && uv run pytest -q && uv run ruff check && uv run ruff format --check` (expected: PASS)
**Commit**: `docs(reports): record the loader probes and their findings`
