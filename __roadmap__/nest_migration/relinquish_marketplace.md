# Relinquish Marketplace

**Goal**: Stop this repository from declaring the `cracking-shells` marketplace, and point every install instruction at Nest instead.
**Pre-conditions**:
- [ ] Nest lists both `colgrep-mcp` and `colgrep-mcp-dev`, verified by reading Nest's marketplace files
- [ ] The playbook campaign's end-to-end install verification is done
**Success Gates**:
- ⬜ `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json` no longer exist [run]
- ⬜ `.claude-plugin/plugin.json` and `.claude-plugin/mcp.json` still exist and are untouched [run]
- ⬜ No file in the repo still contains `marketplace add CrackingShells/colgrep-mcp` [run]
- ⬜ README carries a migration note telling existing users to remove the old marketplace first [run]
**References**: [R02 §namespaces](https://github.com/CrackingShells/cracking-shells-playbook/blob/main/skills/spawning-agent-plugins/references/traps.md#namespaces) — a client keeps the marketplace name it had at add time

## Step 1: Delete the two marketplace files

**Goal**: Leave exactly one repository in the organisation declaring `cracking-shells`.

**Implementation Logic**:
Delete `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`. Delete only these two: `.claude-plugin/plugin.json` and `.claude-plugin/mcp.json` are this plugin's own manifests and must survive — a plugin stops *publishing a catalogue*, it does not stop being a plugin. Both files currently declare `name: "cracking-shells"`, and the Claude one lists `colgrep-mcp` plus `colgrep-mcp-dev`; confirm both names appear in Nest's catalogue before deleting, because after this commit nothing in this repository records that the dev plugin was ever published.
**Deliverables**: deletion of `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`
**Consistency Checks**: `test ! -f .claude-plugin/marketplace.json && test ! -f .agents/plugins/marketplace.json && test -f .claude-plugin/plugin.json` (expected: PASS)
**Commit**: `refactor(marketplace): hand the cracking-shells catalogue to CrackingShells/Nest`

## Step 2: Repoint the install instructions

**Goal**: Stop telling readers to add a marketplace this repo no longer serves.

**Implementation Logic**:
Rewrite the README's install section so both harnesses add `CrackingShells/Nest` rather than `CrackingShells/colgrep-mcp`; the right-hand side of `colgrep-mcp@cracking-shells` is unchanged, because the marketplace name is the same — only its home moved. Add a migration note for existing users: a client keeps whichever marketplace it registered under a name at add time, so anyone who added `cracking-shells` from this repo must run `claude plugin marketplace remove cracking-shells` before adding Nest, or they will silently keep the old two-plugin catalogue. Sweep the whole repository, not just the README — the install snippet is reproduced in `dev/README.md` and may appear in reports.
**Deliverables**: `README.md` — install section repointed at Nest, new migration subsection; any other file carrying the old snippet
**Consistency Checks**: `test $(grep -rl "marketplace add CrackingShells/colgrep-mcp" . --exclude-dir=.git | wc -l) -eq 0` (expected: PASS)
**Commit**: `docs(readme): point installs at the Nest marketplace and note the migration`
