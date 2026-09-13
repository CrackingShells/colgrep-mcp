# index_housekeeping — reports

Seventh campaign of this repository (2026-09-13, after `harness_wiring` 0.4.0): give agents the facts and the one tool needed to keep colgrep's index store lean — size, age, path-exists and shadowing per index, an `index_prune` tool with a dry run and grouped candidates, a `housekeeping` prompt, a `doctor` hint — plus the changelog fix carried from the previous cycle. Single-agent, no roadmap tree: step commits on `claude/dreamy-austin-2682cd`.

## Round 00
- `00-architecture_v0.md` — R01 (index_housekeeping): store discovery from the `Index:` line (C1), the store entry model (C2), the ordered classification (C3), the enriched `list_indexes` (C4), `index_prune` and its deletion guard (C5), the `doctor` hint (C6), the prompt and skill (C7), the changelog pattern (C8); decisions D1–D11; risk register; step-commit plan.
- `00-findings_clear_probe_v0.md` — R02 (index_housekeeping): `colgrep clear` on a gone path exits 1 and leaves the index directory; store layout, mtime and cost facts measured on the maintainer's machine.

## Status
Open. Time-boxed to four hours from 12:54 CEST on 2026-09-13.
