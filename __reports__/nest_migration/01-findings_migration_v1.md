# Nest Migration — Findings (v1)

Date: 2026-09-16

---
type: findings
topic: nest_migration
date: 2026-09-16
version: v1
prior-version: __reports__/nest_migration/00-findings_migration_v0.md
key-metric: plugins installable from Nest as published: 7 of 7 (prior: 6, delta: +1)
decision-required: confirm
---

## Headline Result

metric: plugins installable from Nest as published
value: 7
unit: of 7 catalogue entries
prior: 6
direction: up

The v0 blocker is closed. Nest `2ebd2bc` gives `colgrep-mcp` an explicit HTTPS
`url` source; no entry uses the `github` shorthand any more. The migration now
installs end to end from the published catalogue.

## Results Tables

### Leaf success gates, re-run against the published catalogue

| Gate | v0 | v1 | Evidence |
|:--|:--|:--|:--|
| `colgrep-mcp` installs from Nest as published | ❌ | ✅ | uninstalled first, then reinstalled — the v0 pass came from a local cache edit and proved nothing |
| `colgrep-mcp-dev` installs from Nest | ✅ | ✅ | 0.5.1, user scope, enabled |
| No `failed to load` | ✅ | ✅ | count = 0 across all installed plugins |
| No duplicate-hooks failure | ✅ | ✅ | no `duplicate` line, on a release where the hooks manifest changed shape |
| Server connects | ✅ | ✅ | `plugin:colgrep-mcp:colgrep: uvx colgrep-mcp==0.5.1 - ✔ Connected` |
| All catalogue entries install | not run | ✅ | 7 of 7 installed and enabled |
| Hook fires at the start of a fresh session | ⚠️ | ⚠️ **still unverified** | `claude -p` → `OAuth session expired`, retried and failed again |

### Published entry shapes at Nest `2ebd2bc`

| Entries | Source shape | Transport | Shorthand |
|:--|:--|:--|:--|
| 5 playbook plugins, `colgrep-mcp-dev` | `git-subdir` + HTTPS url | HTTPS | none |
| `colgrep-mcp` | `url` + HTTPS url | HTTPS | none |
| **total using `github` shorthand** | — | — | **0** (was 1) |

### Freshly installed artifact, from the published entry

| Property | Observed |
|:--|:--|
| version | `0.5.1` |
| Claude manifest `hooks` | `./hooks/worktree-remove.json` |
| `extensions["com.openai"]` | present, `hooks` → `./hooks/hooks.json`, 7 interface keys |
| `.codex-plugin/`, `marketplace.json`, `.agents/` | all absent |

## Observations

| Signal | Baseline / Expected | Observed | Interpretation |
|:--|:--|:--|:--|
| Install from published catalogue | Works after the Nest fix | Works, but only proven by uninstalling first [source: `claude plugin uninstall` then `install`] | The v0 install had come via a local cache edit. Re-testing without the uninstall would have re-confirmed the workaround, not the fix — a pass that measures the wrong artifact |
| Shared checkout state | On `ef54b8f`, blocking the playbook's guard entry | Already on `a75fb36`, clean, extensions present, marketplace files gone [source: `git log`, content probe] | The playbook's stated blocker no longer holds; no fast-forward was needed |
| Playbook guard with the entry dropped | Unknown | **PASS** [source: their own `test_spec_regenerates_manifests()` re-run in memory with `ALLOWED_DIVERGENCE = {"dev/README.md": None}`] | Verified without editing their file. They can drop the entry now |
| Fresh-session hook | Verifiable via `claude -p` | Blocked twice by an expired OAuth session [source: `claude -p` output] | Environment fault, unrelated to the migration. The only gate still open |

## Contradictions & Surprises

- The v0 report's `colgrep-mcp` install had to be **discarded as evidence**. It
  succeeded through a local cache edit, so re-running the gate without first
  uninstalling would have measured the workaround and passed for the wrong
  reason — the marketplace-level twin of running a suite against the wrong
  checkout.
- The playbook held its guard entry back on the belief that the shared checkout
  was stale. It was already current. The block was real when reasoned about and
  stale by the time it was acted on.

## Outstanding user actions

| Action | Who | Why |
|:--|:--|:--|
| Drop `ALLOWED_DIVERGENCE["plugin.json"]` from the playbook's regeneration guard | playbook campaign | Verified green with it removed, against the shared checkout at `a75fb36` |
| Re-authenticate Claude Code, then confirm the hook fires in a fresh session | maintainer | The one gate this campaign cannot close; `claude -p` fails with an expired OAuth session |
| Release `v0.5.2` | maintainer | `cz`-computed. Independent of the migration — the `0.5.1` pin is live on PyPI — but Codex reinstalls only on a version change, so the reshaped manifest reaches Codex users only once a release ships |
| Decide whether `refactor` should bump in `[tool.commitizen].bump_map` | maintainer | It does not today, so this campaign's headline change contributed no version bump; the patch came from incidental `fix` commits |
| Existing users: `marketplace remove cracking-shells` before adding Nest | end users | A client keeps whichever marketplace it registered under a name at add time |

## Steering Questions

- **[now]** Release `v0.5.2`? The install path works for real users now, so the
  reason to hold has gone.
- **[now]** Close the campaign with the hook gate recorded as unverified, or
  hold `install_check` open until OAuth is usable and it can be exercised?
- **[later]** Report the two Claude Code behaviours upstream as documentation
  gaps: transport differing between marketplace- and plugin-level `github`
  sources, and `plugin validate` silently validating only the first manifest it
  finds.

## Pointers

- [v0 findings](00-findings_migration_v0.md) — the blocker as first measured
- [Campaign roadmap](../../__roadmap__/nest_migration/README.md)
- [PR #15](https://github.com/CrackingShells/colgrep-mcp/pull/15) — merged as `a75fb36`
- [Nest `2ebd2bc`](https://github.com/CrackingShells/Nest) — the entry fix
- [`stack-traps#oauth`](../../dev/skills/stack-traps/references/claude-code.md) — why the last gate is open
