# hook_namespace

Reports of the hook-namespace cycle: VS Code / Copilot read an Agent Plugins v1
plugin's hooks only from `com.github.copilot/hooks/hooks.json`, which this
repository did not ship (see R01 §Evidence). One campaign fixes that here and
probes the loaders afterwards.

## Documents

| Round | Document | Status |
|:--|:--|:--|
| 00 | `00-architecture_v0.md` — contracts, evidence chain, alternatives, risk register (report id `R01`) | **latest** |
| 01 | `01-findings_loader_probes_v0.md` — loader probes, verdicts and their findings | **latest** |
| 01 | `01-knowledge_transfer_v0.md` — cycle retrospective, next-cycle list | **latest** |

## Status

All three reports are written; the cycle closed on this branch.
Revisions land as `<round>-<name>_v<n+1>.md` at a new round prefix (never overwrite).
