# Nest Migration — Findings (v0)

Date: 2026-09-16

---
type: findings
topic: nest_migration
date: 2026-09-16
version: v0
prior-version: none
key-metric: plugins installable from Nest as published: 6 of 7 (prior: N/A, delta: N/A)
decision-required: intervene
---

## Headline Result

metric: plugins installable from Nest as published
value: 6
unit: of 7 catalogue entries
prior: N/A (first run)
direction: new

`colgrep-mcp` — the entry this campaign exists to serve — is the one that
cannot install. The cause is in Nest's entry, not in this repository. Every
gate that concerns this repository's own manifests passes.

## Results Tables

### Install outcome per catalogue entry, as published

| Entry | Source shape | Transport chosen | Install |
|:--|:--|:--|:--|
| `managing-roadmaps` | `git-subdir` + HTTPS url | HTTPS | ✅ 1.0.0 |
| `writing-history` | `git-subdir` + HTTPS url | HTTPS | ✅ 1.0.0 |
| `writing-release` | `git-subdir` + HTTPS url | HTTPS | ✅ 1.0.0 |
| `writing-reports` | `git-subdir` + HTTPS url | HTTPS | ✅ 1.0.0 |
| `spawning-agent-plugins` | `git-subdir` + HTTPS url | HTTPS | ✅ 1.0.0 |
| `colgrep-mcp-dev` | `git-subdir` + HTTPS url | HTTPS | ✅ 0.5.1 |
| `colgrep-mcp` | `github` + `repo` shorthand | **SSH** | ❌ `Permission denied (publickey)` |

### Leaf success gates

| Gate | Result | Evidence |
|:--|:--|:--|
| `claude plugin list` shows no `failed to load` | ✅ | count = 0 across all installed plugins |
| `claude mcp list` reports the server connected | ✅ | `plugin:colgrep-mcp:colgrep: uvx colgrep-mcp==0.5.1 - ✔ Connected` |
| `colgrep-mcp-dev` installable from Nest | ✅ | installed 0.5.1, user scope, enabled |
| `colgrep-mcp` installable from Nest **as published** | ❌ | SSH clone refused; installs only after a local source-shape change |
| Search policy hook fires at the start of a fresh session | ⚠️ **not verified** | `claude -p` → `OAuth session expired`; see Validated only |

### Installed artifact shape (`cache/cracking-shells/colgrep-mcp/0.5.1/`)

| Property | Expected | Observed |
|:--|:--|:--|
| `.claude-plugin/plugin.json` version | `0.5.1` | `0.5.1` |
| Claude manifest `hooks` | per-event file only | `./hooks/worktree-remove.json` |
| Root `plugin.json` → `extensions["com.openai"]` | present | present |
| `extensions["com.openai"].hooks` | portable file | `./hooks/hooks.json` |
| `interface` block keys | 7 | 7 (capabilities, category, defaultPrompt, developerName, displayName, longDescription, shortDescription) |
| `.codex-plugin/` | absent | absent |
| `.claude-plugin/marketplace.json` | absent | absent |
| `.agents/` | absent | absent |

## Exercised

Run live, against the real marketplace-install path, in Claude Code:

| What | Evidence |
|:--|:--|
| Marketplace resolves to Nest, by source not name | `known_marketplaces.json` → `{"source":"github","repo":"CrackingShells/Nest"}` |
| Catalogue refresh from the published Nest | `claude plugin marketplace update cracking-shells` → success; 7 entries |
| `colgrep-mcp-dev` install from Nest | success, 0.5.1 |
| `colgrep-mcp` install from Nest, **after** a local source-shape change | success, 0.5.1 |
| No plugin fails to load; no duplicate-hooks failure | `failed to load` count 0; no `duplicate` line |
| MCP server starts under the published pin | `uvx colgrep-mcp==0.5.1 - ✔ Connected` |
| Installed artifact carries the reshaped manifests | table above, read from the installed tree |
| Hook script behaviour, from the **installed** artifact | `SessionStart` emits the policy; `PreToolUse` denies `Grep` and `rg <dir>` with the intended reasons |
| Merge is visible to an installer | `git ls-remote https://…/colgrep-mcp.git HEAD` → `a75fb36` |

The duplicate-hooks class of failure — which this repository hit at 0.4.0 and
0.5.0, and which only a real marketplace install reproduces — did **not** fire,
on a release where the hooks manifest changed shape.

## Validated only

Not exercised live; the basis is stated so it is not mistaken for observation.

| Claim | Basis | Why not exercised |
|:--|:--|:--|
| The hook fires at the start of a fresh session | The installed script produces correct `SessionStart` and `PreToolUse` output when fed the harness's JSON by hand, and the installed manifests name the hook files correctly | `claude -p` fails with `OAuth session expired and could not be refreshed` (`stack-traps#oauth`). Script behaviour and manifest wiring are proven; harness-level firing is not |
| Every Codex claim | Published manifest format and the Codex loader's documented parsing of a root Agent-Plugins manifest plus `extensions["com.openai"]` | No Codex CLI on this machine |
| `plugin`-source `github` → SSH is intended behaviour | Observed transport plus the absence of any documentation either way | Claude Code's docs do not specify the transport for any source shape |

## Observations

| Signal | Baseline / Expected | Observed | Interpretation |
|:--|:--|:--|:--|
| `github` shorthand transport | Same as the marketplace-level shorthand, i.e. HTTPS | Plugin-level resolved to `git@github.com:`; marketplace-level clone remote is `https://github.com/CrackingShells/Nest.git` [source: cached clone `git remote -v`; install error text] | Claude Code uses different transports for the same source shape at the two levels. Not a credential fault: the same shorthand succeeded over HTTPS on this machine |
| `gh auth` / credential helper | Honoured for plugin clones | Ignored: `gh auth status` reports logged in with `Git operations protocol: https`, helper `osxkeychain`, yet SSH was attempted [source: `gh auth status`, `git config credential.helper`] | No credential configuration fixes this. Only adding an SSH key would, which is a workaround, not a fix |
| Coverage of the upstream `end_to_end` gate | Nest proven to install every entry | Five playbook entries and colgrep-mcp's *listing* were verified; colgrep-mcp's *install* was not [source: upstream report; entry shapes] | "Lists the plugin" and "installs the plugin" are different claims. All five verified entries share the HTTPS shape, so the defect had no counter-example |
| Installed set after the marketplace was re-pointed | Both colgrep plugins still installed | Both had silently dropped out; this session kept working only from its startup load [source: `claude plugin list` before install] | The silent-replace hazard the campaign exists to remove occurred during the transition itself |
| `github`-shorthand plugin entries elsewhere | Several, as positive controls | Exactly one across every installed marketplace — Nest's `colgrep-mcp` [source: sweep of cached marketplace manifests] | Nothing on this machine could have revealed the defect earlier |

## Contradictions & Surprises

- The entry that failed is the only one of seven using the shorthand, and it is
  the campaign's own plugin. Nest's **Codex** file already gives `colgrep-mcp`
  an explicit HTTPS `url` source; only the Claude file uses the shorthand, so
  the two halves of the same catalogue disagree about how to reach one repo.
- `colgrep-mcp` was not installed at all when this check began. The migration
  had already cost the plugin its installed status, silently, before anything
  was tested.
- A gate this repository has trusted for its whole history was weaker than it
  read: `claude plugin validate .` validates one manifest, prefers the
  marketplace, and stops — so it never checked the plugin manifest while a
  marketplace existed (`stack-traps#validate-picks-one`).

## Outstanding user actions

| Action | Who | Why |
|:--|:--|:--|
| Change Nest's Claude-side `colgrep-mcp` entry to an explicit HTTPS source | Nest / playbook campaign | Until then the documented install path in this repository's README fails for every user without a GitHub SSH key. Verified fix: `{"source": "url", "url": "https://github.com/CrackingShells/colgrep-mcp.git"}` |
| Re-run `claude plugin marketplace update cracking-shells` after that lands | any installer | This machine's catalogue cache currently holds a **local, unpushed** edit carrying the verified fix. A refresh before Nest is fixed restores the broken entry |
| Existing users: `claude plugin marketplace remove cracking-shells` before adding Nest | end users | A client keeps whichever marketplace it registered under a name at add time, so skipping the remove silently keeps the old two-plugin catalogue with no error |
| Confirm the hook fires in a fresh session once OAuth is usable | maintainer | The one gate this report cannot close |
| Decide whether `refactor` should bump in `[tool.commitizen].bump_map` | maintainer | It does not today, so a manifest-shape change under a `refactor` subject produces no release — and Codex's reinstall gate compares version strings, so such a change would never reach a Codex user |

## Steering Questions

- **[now]** Fix Nest's `colgrep-mcp` entry, or leave the catalogue installable
  only for SSH users? The verified fix is one line and matches the other six
  entries plus Nest's own Codex file.
- **[now]** Should the upstream `end_to_end` gate be re-run with an
  install-every-entry check rather than install-the-five-and-list-the-rest? The
  same gap would hide any future entry that uses the shorthand.
- **[next run]** Does `v0.5.2` ship before or after Nest is fixed? The release
  is independent — the pin is already `0.5.1` and live — but shipping a README
  whose install path fails is a worse artifact than waiting.
- **[later]** Is `refactor` genuinely a non-bumping type here, given Codex
  reinstalls only on a version change?
- **[later]** Worth reporting the transport inconsistency and the
  validate-picks-one behaviour upstream to Anthropic as documentation gaps.

## Pointers

- [Campaign roadmap](../../__roadmap__/nest_migration/README.md)
- [Install check leaf](../../__roadmap__/nest_migration/verify/install_check.md)
- [PR #15](https://github.com/CrackingShells/colgrep-mcp/pull/15) — the migration, merged as `a75fb36`
- [`stack-traps#validate-picks-one`](../../dev/skills/stack-traps/references/claude-code.md) — the masked gate
- [`stack-traps#oauth`](../../dev/skills/stack-traps/references/claude-code.md) — why the fresh-session gate could not run
- [Nest catalogue](https://github.com/CrackingShells/Nest) — where the outstanding fix belongs
