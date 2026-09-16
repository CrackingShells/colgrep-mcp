# nest_migration reports

Reports for the campaign that handed the `cracking-shells` marketplace name to
`CrackingShells/Nest` and moved this repository's manifests to the reshaped
generator's output.

## Round 00

| Document | Type | Latest |
|:--|:--|:--|
| [00-findings_migration_v0.md](00-findings_migration_v0.md) | findings | ✅ latest |

## Status

The migration is **merged** (PR #15, `a75fb36`) and this repository is complete:
no marketplace files, Codex served through `extensions["com.openai"]`, installs
repointed at Nest with a migration note.

One item is outstanding and lives **outside this repository**: Nest's
Claude-side `colgrep-mcp` entry uses the `github` + `repo` shorthand, which
Claude Code clones over SSH, so the install fails for anyone without a GitHub
SSH key. Six of seven entries already use an explicit HTTPS source, and the
fix has been verified locally. Until it lands in Nest, the install path this
repository's README documents does not work for HTTPS-only users.

One gate could not be closed here: whether the search-policy hook fires at the
start of a fresh session. `claude -p` fails with an expired OAuth session on
this machine (`stack-traps#oauth`), so the hook was exercised by feeding the
installed script the harness's JSON instead. Script behaviour and manifest
wiring are proven; harness-level firing is not.
