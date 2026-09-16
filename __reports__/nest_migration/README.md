# nest_migration reports

Reports for the campaign that handed the `cracking-shells` marketplace name to
`CrackingShells/Nest` and moved this repository's manifests to the reshaped
generator's output.

## Round 00

| Document | Type | Latest |
|:--|:--|:--|
| [00-findings_migration_v0.md](00-findings_migration_v0.md) | findings | superseded by v1 |

## Round 01

| Document | Type | Latest |
|:--|:--|:--|
| [01-findings_migration_v1.md](01-findings_migration_v1.md) | findings | ✅ latest |

## Status

The migration is **complete and installable**. Merged as `a75fb36` (PR #15):
no marketplace files here, Codex served through `extensions["com.openai"]`,
`.codex-plugin/` retired, installs repointed at Nest with a migration note.

All seven Nest entries install, including `colgrep-mcp`. The v0 blocker — its
catalogue entry using the `github` shorthand, which Claude Code clones over
SSH — was fixed in Nest `2ebd2bc` and re-tested here after uninstalling first,
so the pass measures the published catalogue rather than the local workaround
that produced v0's result.

One gate is recorded as unverified rather than inferred: whether the
search-policy hook fires at the start of a fresh session. `claude -p` fails
with an expired OAuth session on this machine (`stack-traps#oauth`), retried
and failed again. The installed hook script was exercised directly instead — it
emits the policy on `SessionStart` and denies both `Grep` and a shell corpus
search on `PreToolUse` — so script behaviour and manifest wiring are proven and
harness-level firing is not.
