# Regenerate Manifests

**Goal**: Move this repository's manifests to the reshaped generator's output — a root Agent-Plugins `plugin.json` carrying `extensions["com.openai"]`, with `.codex-plugin/` gone and no marketplace written back.
**Pre-conditions**:
- [ ] `agent_plugin_nest/generator/generator_reshape.md` is merged and its regeneration guard is green on the new baseline
- [ ] A playbook checkout containing the **reshaped** generator is available; its absolute path is named in the brief
**Success Gates**:
- ⬜ No `.codex-plugin/` directory remains [run]
- ⬜ Root `plugin.json` carries `extensions["com.openai"]` with the full interface block [run]
- ⬜ Regenerating writes no marketplace file into this repository [run]
- ⬜ `check_plugin.py` reports no problems [run]
- ⬜ The version in every manifest is still `0.5.1`; this leaf reshapes, it does not release [run]
**References**: [R01 §Decisions already settled](~/.claude/plans/good-news-overall-it-s-gleaming-wreath.md) — why the extensions namespace replaces `.codex-plugin/`

## Step 1: Switch the spec to hub mode

**Goal**: Stop the spec from declaring a marketplace, so regeneration cannot resurrect one.

**Implementation Logic**:
The spec still carries `claude_marketplace` and `codex.marketplace_name`, which is what made this repository the owner of the `cracking-shells` name. Replace them with the generator's hub mode, so `spawn` writes no `.claude-plugin/marketplace.json` and no `.agents/plugins/marketplace.json`.

This step exists because of an ordering hazard, and skipping it is silent: regenerating with the old spec writes both marketplace files back, undoing `relinquish_marketplace` without any error, and leaving two repositories declaring one marketplace name again — the exact condition this whole migration removes. With hub mode set, the two leaves become genuinely order-independent.
**Deliverables**: the spec consumed by `spawn` (the playbook's `assets/examples/colgrep-mcp.spec.json`, or a repo-local copy if the implementer prefers not to edit the skill's example) — `claude_marketplace` and `codex.marketplace_name` replaced by the hub-mode key
**Consistency Checks**: `test ! -f .claude-plugin/marketplace.json || echo "marketplace still present - relinquish has not run yet, which is allowed"` (expected: PASS)
**Commit**: `refactor(plugin): declare hub mode so no marketplace is generated here`

## Step 2: Regenerate with the reshaped generator

**Goal**: Produce the new manifest shape from the spec rather than by hand.

**Implementation Logic**:
Run the reshaped `spawn_plugin.py --root . spawn --spec <spec> --force` from **the playbook checkout that contains the reshape**. Running the unextended generator would regenerate the old three-manifest shape and appear to succeed; the brief must name the path explicitly, and the implementer should confirm the generator it invoked actually emits `extensions` rather than `.codex-plugin/` before trusting the result.

`--force` is required because the manifests already exist and `put` refuses to overwrite without it. With hub mode set in step 1 there is no `merge_marketplace` call for `--force` to turn destructive, which is the whole reason step 1 comes first. Afterwards delete the `.codex-plugin/` directory: the new generator no longer writes it, but it does not remove what an earlier run left behind.
**Deliverables**: `plugin.json` — `extensions["com.openai"]` containing the interface block and the Codex hooks path; `.claude-plugin/plugin.json` unchanged in shape; deletion of `.codex-plugin/`
**Consistency Checks**: `test ! -d .codex-plugin && python3 -c "import json;d=json.load(open('plugin.json'));assert 'com.openai' in d['extensions']"` (expected: PASS)
**Commit**: `refactor(plugin): express Codex through the com.openai extensions namespace`

## Step 3: Check the tree against itself

**Goal**: Confirm the reshape left a self-consistent plugin, not merely a changed one.

**Implementation Logic**:
Run `check_plugin.py` and `claude plugin validate .` over the repo. Confirm the version is still `0.5.1` everywhere including the `uvx` pin in the MCP manifests — this leaf changes manifest *shape*, and a version move here would desynchronise the pin from the published artifact and break every launch until a release caught up. Confirm no marketplace file reappeared. Do not point Claude's validator at anything but the Claude manifest and the repo root; it rejects the Codex `interface` block as an unknown field, which is a false alarm rather than a finding.
**Deliverables**: no new files — validator output recorded in the commit body
**Consistency Checks**: `python3 -c "import json;d=json.load(open('plugin.json'));assert d['version']=='0.5.1'" && test ! -f .claude-plugin/marketplace.json` (expected: PASS)
**Commit**: `test(plugin): verify the reshaped manifests are self-consistent`
