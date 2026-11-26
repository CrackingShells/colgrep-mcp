# hook_namespace

Reports of the hook-namespace cycle: VS Code / Copilot read an Agent Plugins v1
plugin's hooks only from `com.github.copilot/hooks/hooks.json`, which this
repository did not ship (see R01 §Evidence). One campaign fixes that here and
probes the loaders afterwards.

## Documents

| Round | Document | Status |
|:--|:--|:--|
| 00 | `00-architecture_v0.md` — contracts, evidence chain, alternatives, risk register (report id `R01`) | **latest** |
| 01 | `01-observation_loader_probes_v0.md` — loader probes and their findings | planned |
| 01 | `01-knowledge_transfer_v0.md` — cycle retrospective | planned |

## Status

Round 00 is written and committed on the campaign branch; both leaves and the
probe level run against it. Revisions of `00-architecture_v0.md` land as
`0X-architecture_v1.md` (naming rule: never overwrite).
