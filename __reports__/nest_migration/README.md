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

**The last gate is now closed.** Both findings reports record the
fresh-session hook check as unverified, because `claude -p` failed twice with
an expired OAuth session (`stack-traps#oauth`). After re-authentication it was
exercised for real: a fresh `claude -p` session, running the plugin installed
from the published catalogue, received the `SessionStart` context and quoted it
back verbatim —

> "Denied in this session: the built-in Grep tool, and shell CORPUS searches
> (grep -r, rg, find -exec grep, xargs grep)."

So harness-level firing is confirmed, not just script behaviour and manifest
wiring. Every gate in `verify/install_check` has now been exercised live. This
note is the record of that closure; the reports themselves are left as written,
since a finding is a statement about what was known when it was made.
