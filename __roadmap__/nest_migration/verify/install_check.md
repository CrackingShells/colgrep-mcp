# Install Check

**Goal**: Prove colgrep-mcp installs from Nest with its server connected and its hooks firing, closing the migration.
**Pre-conditions**:
- [ ] `relinquish_marketplace` and `regenerate_manifests` are both merged and pushed — a git source resolves against the remote, not the worktree
- [ ] The local `cracking-shells` registration already points at `CrackingShells/Nest`
**Success Gates**:
- ⬜ `claude plugin list` shows `colgrep-mcp` with no `failed to load` line [run]
- ⬜ `claude mcp list` reports the colgrep server connected [run]
- ⬜ The search policy hook fires at the start of a fresh session [behavioral]
- ⬜ `colgrep-mcp-dev` is installable from Nest as well [run]
**References**: [R02 §hooks-manifest-duplicate](https://github.com/CrackingShells/cracking-shells-playbook/blob/main/skills/spawning-agent-plugins/references/traps.md#hooks-manifest-duplicate) — why only a marketplace install reproduces this failure

## Step 1: Install from Nest and read the load state

**Goal**: Exercise the path that no tree-level command reproduces.

**Implementation Logic**:
Reinstall `colgrep-mcp@cracking-shells` from Nest and read `claude plugin list`. This is the only path that surfaces "Duplicate hooks file detected": `--plugin-dir`, `plugin details` and `plugin validate` all accept a tree that fails a real marketplace install, and this repo has hit exactly that failure before, at 0.4.0 and 0.5.0. Install `colgrep-mcp-dev` too — it moved catalogues in this migration and has never been installed from Nest.

Then confirm the server actually starts with `claude mcp list`, and open a fresh session to confirm the search policy hook fires. A plugin can load with its hooks silently inert, which is the failure this check exists to catch.
**Deliverables**: no files — observed outputs recorded in the commit body
**Consistency Checks**: `claude plugin list 2>&1 | grep -c "failed to load" | grep -qx 0` (expected: PASS)
**Commit**: `test(plugin): verify colgrep-mcp installs from the Nest marketplace`

## Step 2: Record what the migration proved

**Goal**: Close the campaign with an honest account of what was exercised.

**Implementation Logic**:
Write a findings report under `__reports__/nest_migration/`. Separate what was exercised live in Claude Code — marketplace install, server connection, hooks firing — from what was only validated statically. No Codex CLI is available here, so every Codex claim rests on the published manifest format and the loader source, and must be labelled as such; `manifests.md` already keeps a verification-status table that draws this line, and it must not blur now that the catalogue has moved. Note any user-visible migration step still outstanding, in particular that existing clients keep the old marketplace until they remove it by hand.
**Deliverables**: `__reports__/nest_migration/00-findings_migration_v0.md` — sections Exercised, Validated only, Outstanding user actions
**Consistency Checks**: `test -f __reports__/nest_migration/00-findings_migration_v0.md` (expected: PASS)
**Commit**: `docs(reports): record the Nest migration outcome and its limits`
