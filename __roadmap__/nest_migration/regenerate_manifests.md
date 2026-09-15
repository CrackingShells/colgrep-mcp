# Regenerate Manifests

**Goal**: Move this repository's manifests to the reshaped generator's output — a root Agent-Plugins `plugin.json` carrying `extensions["com.openai"]`, with `.codex-plugin/` gone.
**Pre-conditions**:
- [ ] A playbook checkout containing the **reshaped** generator is available; its absolute path is named in the brief
- [ ] `agent_plugin_nest/generator/generator_reshape.md` is done and its regeneration guard is green on its new baseline
**Success Gates**:
- ⬜ No `.codex-plugin/` directory remains [run]
- ⬜ Root `plugin.json` carries `extensions["com.openai"]` with the full interface block [run]
- ⬜ `check_plugin.py` reports no problems [run]
- ⬜ `claude plugin validate .` passes [run]
- ⬜ The version in every manifest is still `0.5.1`; this leaf reshapes, it does not release [run]
**References**: [R01 §Decisions already settled](~/.claude/plans/good-news-overall-it-s-gleaming-wreath.md) — why the extensions namespace replaces `.codex-plugin/`

## Step 1: Regenerate with the reshaped generator

**Goal**: Produce the new manifest shape from the spec rather than by hand.

**Implementation Logic**:
Run the reshaped `spawn_plugin.py --root . spawn --spec <playbook>/skills/spawning-agent-plugins/assets/examples/colgrep-mcp.spec.json --force` from **the playbook checkout that contains the reshape**. Running the unextended generator instead would regenerate the old three-manifest shape and appear to succeed — the brief must name the path explicitly and the implementer should confirm the generator it invoked actually emits `extensions`, not `.codex-plugin/`.

`--force` is required because the manifests already exist and `put` refuses to overwrite without it. `--force` is safe for `put`, but it also makes `merge_marketplace` replace a marketplace wholesale — harmless here only because `relinquish_marketplace` has already deleted both marketplace files. If they are still present, stop and report it rather than forcing.

Afterwards, delete the `.codex-plugin/` directory, which the new generator no longer writes but also does not remove.
**Deliverables**: `plugin.json` — `extensions["com.openai"]` containing the interface block and the Codex hooks path; `.claude-plugin/plugin.json` unchanged in shape; deletion of `.codex-plugin/`
**Consistency Checks**: `test ! -d .codex-plugin && python3 -c "import json;d=json.load(open('plugin.json'));assert 'com.openai' in d['extensions']"` (expected: PASS)
**Commit**: `refactor(plugin): express Codex through the com.openai extensions namespace`

## Step 2: Check the tree against itself

**Goal**: Confirm the reshape left a self-consistent plugin, not just a changed one.

**Implementation Logic**:
Run `check_plugin.py` and `claude plugin validate .` over the repo. Confirm the version is still `0.5.1` everywhere including the `uvx` pin in the MCP manifests — this leaf changes manifest *shape*, and a version move here would desynchronise the pin from the published artifact and break every launch until a release caught up. Do not point Claude's validator at anything but the Claude manifest and the repo root; it rejects the Codex `interface` block as an unknown field, which is a false alarm rather than a finding.
**Deliverables**: no new files — validator output recorded in the commit body
**Consistency Checks**: `python3 -c "import json,re;d=json.load(open('plugin.json'));assert d['version']=='0.5.1'"` (expected: PASS)
**Commit**: `test(plugin): verify the reshaped manifests are self-consistent`
