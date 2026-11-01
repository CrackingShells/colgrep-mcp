# Reports — match_units

## Round 00
- `00-findings_upstream_colgrep_contract_v0.md` — four upstream colgrep asks, most valuable first: a per-unit content hash in `matches`, the best unit kept first on ties, the index-update outcome reported under `--json`, and a merge across search paths. Each comes with colgrep source lines, the server workaround it would remove, the gaps accepted today, and what not to ask (latest)
- `00-knowledge_transfer_v0.md` — the rework cycle on PR #18: what shipped, what the reviewer, advisor and verifier caught, why both trust-rule designs were wrong, and the next-cycle changes (latest)
- `00-observation_dirtree_rdm_add_suffix_v0.md` — `dirtree-rdm add` without `.md` orphans a leaf file and reports the error at the wrong table; the fix belongs in the managing-roadmaps plugin (latest)

## Status
- **Campaign:** `__roadmap__/match_units/` is closed. All three nodes are done; step 5 (`find_files -k limit`) was skipped on evidence.
- **PR:** [CrackingShells/colgrep-mcp#18](https://github.com/CrackingShells/colgrep-mcp/pull/18) is open, with nothing merged yet.
- **Next:** the upstream asks in the findings report, through the CrackingShells/next-plaid fork. The fork's markdown-sections work is tracked in `__reports__/match_lines/`.
