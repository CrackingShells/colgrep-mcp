# Reports — repo_health

## Round 00
- `00-architecture_v0.md` — contracts C1–C5 for the scaffold: single version source + commitizen, uv-based launch, AGENTS.md, ruff, cross-OS CI; alternatives and risk register (latest)
- `00-findings_launch_placeholders_v0.md` — where each plugin ecosystem expands root placeholders, with quoted spec sentences; motivates moving the Claude Code MCP config to `.claude-plugin/mcp.json` (latest)

## Round 01
- `01-observation_review_v0.md` — read-only reviewer pass over the depth-0 merge: two confirmed commitizen defects (fixed before release), one asymmetry deferred, `cz check --message` probe table (latest)

## Round 02
- `02-knowledge_transfer_v0.md` — retrospective: wins, pain points, root causes, next-cycle changes (PyPI → `uvx`, `ruff format`, Windows CI result, canonical GitHub location, Codex placeholder) (latest)

## Round 03
- `03-findings_ci_matrix_v0.md` — first six CI runs on GitHub: Windows 73 → 19 → 0 failures, causes per layer (one real server fix in `resources.py`), `setup-uv` tag pinning, PR-vs-rebase note (latest)

## Round 04
- `04-findings_remote_install_v0.md` — remote install from GitHub per plugin ecosystem: Claude Code marketplace add + install verified end-to-end, Codex's equivalent documented but not exercised (no Codex CLI here), Agent Plugins 1.0 has no spec-defined mechanism at all (latest)

## Status
Campaign opened and closed 2026-09-12 (≈50 min): two Sonnet implementers on file-disjoint leaves, one Sonnet reviewer, lead did the glue. Released as v0.1.1 through the commitizen machinery the campaign introduced. Same afternoon: relicensed to AGPL-3.0-or-later, pushed to `CrackingShells/colgrep-mcp`, CI green on ubuntu/macos/windows after PR #1.
