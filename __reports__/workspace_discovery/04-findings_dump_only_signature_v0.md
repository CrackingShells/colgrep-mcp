# Dump-only probe signature — Findings (v0)

Date: 2026-11-27

---
type: findings
topic: workspace_discovery
date: 2026-11-27
version: v0
prior-version: none
key-metric: client_visible_dumps_parity: PASS (4/4 lists byte-identical) (prior: N/A, delta: N/A)
decision-required: none
---

## Headline Result

metric: client_visible_dumps_parity
value: PASS — `Client.list_tools()` / `list_resources()` / `list_resource_templates()` /
`list_prompts()` are byte-identical between base and the hardened probe branch with
`COLGREP_MCP_PROBE` unset; the probe is inert at the client-visible surface.
unit: canonicalized listings compared (4)
prior: N/A (this closes the signature debt recorded in the campaign README Gotchas,
2026-11-13 `ca3cb40`)
direction: n/a (invariant discharge)

## Results Tables

### Client-visible listings, base vs task/probe-hardening (probe disabled)

| Listing | n | sha256[:16] base | sha256[:16] branch | Result |
|:--------|--:|:-----------------|:-------------------|:-------|
| tools | 9 | `88714214c2d7908f` | `88714214c2d7908f` | equal |
| resources | 4 | `3c97ad1b6677e9b2` | `3c97ad1b6677e9b2` | equal |
| resource_templates | 1 | `627bc16ed6218d0f` | `627bc16ed6218d0f` | equal |
| prompts | 4 | `078a59b3f2053426` | `078a59b3f2053426` | equal |

## Method

Identical measurement script on both sides: an in-process `mcp.ClientSession` over
stdio against `uv run --quiet --directory server colgrep-mcp`, launched with
`COLGREP_MCP_PROBE` removed from the child environment. Each listing tuple
(name, description, canonical `inputSchema`/URI where applicable) is serialized
with `json.dumps(..., sort_keys=True)` and hashed (`hashlib.sha256`) before
comparison; the digests above are truncated to 16 hex chars for the table.

- base: this worktree's merge base state — `main` as restored at `5b8b099`, whose
  `server/colgrep_mcp/` has no probe facility (withdrawn by `8f9490f`).
- branch: `task/probe-hardening` at `75abe82` (probe re-landed hardened, four
  commits `082e707..75abe82`).
- Run window: 2026-11-27 13:36 JST.

## Interpretation

The dump-only law of `probe_hardening` step 0 holds where a client can see it:
the probe adds no tool, resource, resource template or prompt, and mutates none,
when its env sentinel is unset. The complementary legs are already pinned
in-tree by `test_probe_inert_without_env` (no filesystem writes), the rewritten
`test_no_probe_side_effects` (ledger truth against `forge_record` ground truth),
and `test_tool_call_survives_probe_rename` (resolution paths unchanged with the
probe rename) — this report is the end-to-end MCP-surface leg the campaign
README lists as the pre-condition for dispatching `collect_harness_evidence`.

## Caveat

The two servers self-report versions found outside the leaf's owned files
(base `0.6.1`, branch `0.6.0`, from `pyproject.toml` sits the branch was cut
against); the version literal is not surfaced in any of the four listings
compared here, so parity is unaffected. The manifests/version literals are
written only by `cz bump` (`landing-and-release` §Release) and need no manual
edit. Residual risk: none identified for the probe's client-visible surface.
