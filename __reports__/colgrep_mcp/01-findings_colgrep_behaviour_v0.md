# colgrep CLI Behaviour — Findings (v0)

Date: 2026-09-11

---
type: findings
topic: colgrep_mcp
date: 2026-09-11
version: v0
prior-version: none
key-metric: hit-json-line-field reliability: ~40% correct start line across 30 distinct hits (prior: N/A, delta: N/A)
decision-required: intervene
---

## Headline Result

metric: hit JSON schema stability
value: stable field set (24 `unit` fields + `score`), but `line`/`end_line` are frequently wrong
unit: fields observed across 30 distinct hits from 6 independent invocations
prior: N/A (first run)
direction: new

## Results Tables

### Probe Results

All probes run with `--color never` against a fresh `git clone --depth 1 pallets/click` (152–156 files) under the scratchpad, unless noted. Full stdout/stderr/exit captured per probe in `evidence/colgrep/`.

| # | Probe | Exit | Stdout kind | Stderr kind | Wall time |
|---|---|---|---|---|---|
| 1 | Cold `init -y` | 0 | empty | 3-line index-build summary | 15.07s |
| 2a | Warm `init` (no change) | 0 | empty | 1-line "up to date" | 0.06s |
| 2b | Warm `init` after `touch` (no content change) | 0 | empty | 1-line "up to date" (unchanged!) | 0.08s |
| 3a | `--json -k 3 "query"` | 0 | JSON array, 3 hits | 2-line model/build banner | 15.73s |
| 3b | `--json --content -k 2` | 0 | identical JSON to 3c2 | none | 0.81s |
| 3c | `--json --lines 2 -k 2` | 0 | identical JSON to 3c2 | none | 0.77s |
| 3c2 | `--json -k 2` (no display flags) | 0 | baseline for 3b/3c comparison | none | 0.78s |
| 3d | `--json --files-only -k 2` | 0 | **plain-text file list, not JSON** | none | 0.72s |
| 3e | `--json -e "def.*parse" "query"` | 0 | JSON, hybrid-filtered | none | 0.75s |
| 3f | `--json -e "def parse_args"` (no query) | 0 | JSON, regex-only | none | 0.73s |
| 3g | `--json --include "*.py"` | 0 | JSON | none | 0.75s |
| 3h | `--json --exclude-dir tests` | 0 | JSON | none | 0.75s |
| 3i | `--json -e <no-match regex> "<no-match query>"` | 0 | `[]\n` (3 bytes) | none | 0.58s |
| 3j | `--json` on non-existent path | **1** | empty | `Error: Path does not exist: …` + closest-dir hint | 0.04s |
| 3k | `--json` on a single **file** path | 0 | JSON, 1 hit, scoped to that file | `📋 Seeded index from worktree … re-embedding only changed files` + 2-line banner | 6.69s |
| 3l | `--json` on **two** dir paths | 0 | JSON, merged/ranked results | banner **printed twice** (once per path) | 13.21s |
| 4 | `--json` with `-k` omitted, broad query | 0 | exactly 15 hits | **none** (no truncation notice) | 0.75s |
| 4b | `--json -e "^def "` with `-k` omitted | 0 | 95 hits (not capped at 15) | none | 0.76s |
| 5a | `status <indexed dir>` | 0 | 4-line block, `Project: /private/tmp` | none | 0.07s |
| 5b | `--stats` | 0 | 154 project blocks, global, not scoped | none | 0.12s |
| 5c | `settings` | 0 | 16-line config dump | none | 0.05s |
| 5d | `status <never-indexed dir>` | 0 | "No index found" | none | 0.08s |
| 6a | `init -y` on isolated temp dir (clear-test setup) | 0 | empty | 2-line banner | 0.49s |
| 6 | `clear <isolated dir>` | 0 | 1-line `🗑️ Cleared index for …` | none, **no prompt** | 0.04s |
| 7a/7b | Two concurrent `--json` searches after `touch` | 0 / 0 | both valid JSON, 3 hits each | none | 0.94s (both, wall) |
| 8 | Unicode query + space/CJK path | 0 | JSON, 1 hit, path preserved verbatim | 2-line banner | 3.12s |
| 10a | `env PATH=/usr/bin:/bin sh -c 'colgrep --version'` | **127** | empty | `sh: colgrep: command not found` | instant |
| 10b | `HOME=$(mktemp -d) colgrep …` | — | **ABORTED** — sandbox refuses HOME reassignment (see `evidence/colgrep/10b_freshhome_blocked.note.txt`) | — | — |

### `colgrep --json` hit — fields observed (30 distinct hits, 6 invocations)

| Field | Type(s) observed | Nullable observed |
|---|---|---|
| `score` | float | no |
| `unit.name` | string | no |
| `unit.qualified_name` | string | no |
| `unit.file` | string (absolute path) | no |
| `unit.line`, `unit.end_line` | int | no — but **frequently inaccurate**, see Contradictions |
| `unit.language` | string (`"python"` only in this corpus) | no |
| `unit.unit_type` | string (`function`\|`method`\|`class`\|`rawcode`\|`document` seen) | no |
| `unit.signature` | string | no |
| `unit.docstring` | string \| null | **yes** |
| `unit.parameters` | array[string] | no (empty array when none) |
| `unit.return_type` | string \| null | **yes** |
| `unit.extends` | null (only value observed, 0/30) | **yes** (treat as nullable string) |
| `unit.parent_class` | string \| null | **yes** |
| `unit.calls`, `unit.called_by` | array[string] | no (empty array when none) |
| `unit.complexity` | int | no |
| `unit.has_loops`, `unit.has_branches`, `unit.has_error_handling` | bool | no |
| `unit.variables` | array[string] | no |
| `unit.imports` | array[string] | no |
| `unit.code` | string (verbatim source, always correct — see Contradictions) | no |

## Hit JSON Schema (draft 2020-12)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://colgrep-mcp.internal/schemas/search-hit.json",
  "title": "colgrep search hit",
  "type": "object",
  "additionalProperties": false,
  "required": ["unit", "score"],
  "properties": {
    "score": { "type": "number" },
    "unit": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "name", "qualified_name", "file", "line", "end_line", "language",
        "unit_type", "signature", "docstring", "parameters", "return_type",
        "extends", "parent_class", "calls", "called_by", "complexity",
        "has_loops", "has_branches", "has_error_handling", "variables",
        "imports", "code"
      ],
      "properties": {
        "name": { "type": "string" },
        "qualified_name": { "type": "string", "description": "e.g. 'src/click/core.py::Command::parse_args'" },
        "file": { "type": "string", "description": "absolute path, unicode-safe, verbatim" },
        "line": { "type": "integer", "minimum": 1, "description": "OBSERVED UNRELIABLE for method/function units in large or duplicate-named files — see findings report Contradictions" },
        "end_line": { "type": "integer", "minimum": 1, "description": "OBSERVED UNRELIABLE, same caveat as line" },
        "language": { "type": "string", "description": "one of colgrep's 18+ supported languages; only 'python' observed in this probe run" },
        "unit_type": { "type": "string", "enum": ["function", "method", "class", "rawcode", "document"], "description": "enum extrapolated from observation; colgrep --help does not enumerate this set, treat as open unless confirmed" },
        "signature": { "type": "string" },
        "docstring": { "type": ["string", "null"] },
        "parameters": { "type": "array", "items": { "type": "string" } },
        "return_type": { "type": ["string", "null"] },
        "extends": { "type": ["string", "null"], "description": "only null observed (0/30); non-null shape unconfirmed" },
        "parent_class": { "type": ["string", "null"] },
        "calls": { "type": "array", "items": { "type": "string" } },
        "called_by": { "type": "array", "items": { "type": "string" } },
        "complexity": { "type": "integer", "minimum": 0 },
        "has_loops": { "type": "boolean" },
        "has_branches": { "type": "boolean" },
        "has_error_handling": { "type": "boolean" },
        "variables": { "type": "array", "items": { "type": "string" } },
        "imports": { "type": "array", "items": { "type": "string" } },
        "code": { "type": "string", "description": "verbatim source snippet; observed always correct even when line/end_line are not" }
      }
    }
  }
}
```

## Text-format samples (verbatim, for the adapter's text parsers)

### `colgrep status <dir>` — indexed

```
Project: /private/tmp
  Subdirectory: claude-501/-Users-hacker-Documents-explore-colgrep-mcp/a8c80498-9a50-45ec-b1a2-c45eb195404d/scratchpad/corpus/click
Model:   lightonai/LateOn-Code-edge
Index:   /Users/hacker/Library/Application Support/colgrep/indices/tmp-a825743a

Run any search to update the index, or `colgrep clear` to rebuild from scratch.
```

### `colgrep status <dir>` — not indexed

```
No index found for /private/var/folders/nw/ddpd99c119j47w3s4gzv7sb00000gn/T/colgrep_clear_test [lightonai/LateOn-Code-edge]
Run `colgrep <query>` to create one.
```

### `colgrep settings`

```
Current configuration:

  model:       lightonai/LateOn-Code-edge (default)
  precision:   int8 (build default)
  coreml-cache: (default: ~/Library/Caches/next-plaid/coreml)
  pool-factor: 2 (default)
  parallel:    auto (runtime-resolved)
  batch-size:  auto (runtime-resolved)
  k:           25 (default)
  n:           6 (default)
  verbose:     false (default)
  rel-paths:   true
  hybrid:      true (default)
  alpha:       0.60 (default)
  max-depth:   1024 (default)
  ignore:      .claude/worktrees, **/htn-creator-workspace/results
  force-incl:  (none)

Use --k or --n to set values. Use 0 to reset to default.
[... 8 more "Use --x to ..." lines, verbatim in evidence/colgrep/05c_settings.stdout.txt]
```

### `colgrep --stats` (machine-global, NOT project-scoped — excerpt; full 154-project / 771-line dump in `evidence/colgrep/05b_stats.stdout.txt`)

```
Project: /Users/hacker/Documents/src/LittleCoinCoin/usd-bio/examples/p53_mdm2
  Model: lightonai/LateOn-Code-edge
  Functions indexed: 649
  Search count: 3

Project: /private/tmp
  Model: lightonai/LateOn-Code-edge
  Functions indexed: 2434
  Search count: 11

[... 152 more Project blocks for unrelated projects on this machine ...]

Total: 154 indexes, 138402 functions, 4613 searches
```

The block format per project is fixed: `Project: <path>` / `  Model: <id>` / `  Functions indexed: <int>` / `  Search count: <int>`, blank line separated, with a final `Total: N indexes, M functions, S searches` line.

## Observations

| Signal | Baseline / Expected [source] | Observed [source] | Interpretation |
|---|---|---|---|
| `-k` default result count | `--help`: "default: 15, or 10 if `-n` is used" [`colgrep --help`] | Exactly 15 hits returned for an unbounded broad query with `-k` omitted [`04_json_nok.stdout.txt`] | Matches `--help`, **contradicts** `colgrep settings`' own claim of `k: 25 (default)` [`05c_settings.stdout.txt`] — settings' printed default is stale/wrong relative to runtime behaviour |
| Index storage location | `--help` ENVIRONMENT section: "Indexes are stored in `~/.local/share/colgrep/` (or `$XDG_DATA_HOME/colgrep`)" | Actual: `/Users/hacker/Library/Application Support/colgrep/indices/…` [`05a_status_indexed.stdout.txt`, confirmed on disk] | `--help` documents a Linux XDG path that is not where colgrep actually writes on macOS; adapter must special-case macOS's native `~/Library/Application Support/colgrep` |
| `--json` + `--files-only` interaction | No architecture-report baseline (missing, see Pointers); `--help` lists both flags independently with no stated interaction | `--files-only` silently overrides `--json`, emitting **plain newline-separated paths**, exit 0, no warning [`03d_json_filesonly.stdout.txt`] | Adapter must never pass `--files-only` when it needs machine-readable output — the flag combination is not JSON despite `--json` being present |
| `--content` / `--lines` under `--json` | Presumed these flags shape the JSON payload (they shape terminal display per `--help`) | Byte-identical JSON output with/without `--content` and `--lines N` (3837 bytes across `03b`, `03c`, `03c2`) | Both flags are display-only and no-ops under `--json`; full `unit.code` is always returned regardless |
| Reindex trigger on `touch` | Assumed mtime-based invalidation (common for file watchers) | `touch`ing a tracked file with no content change still reports "Index is up to date" [`02b_warm_init_touched.stderr.txt`] | Reindexing is content-hash based, not mtime-based — adapter cannot rely on touching files to force a refresh; must actually change content |
| Project-root resolution | Assumed: project root = the given PATH argument (or nearest VCS root) | `colgrep status`/`init` on **any** subdirectory of `/private/tmp` resolves `Project:` to `/private/tmp` itself, a pre-existing shared bucket with 2434 functions from prior sessions [`05a_status_indexed.stdout.txt`, `05d_status_notindexed.stdout.txt`, `05b_stats.stdout.txt`] | colgrep appears to walk up from the given path to the nearest **already-registered** ancestor project rather than always rooting at the given directory; once a shallow ancestor (e.g. a whole temp filesystem) is registered by any process, every descendant path folds into it. Confirmed *not* universal: an unregistered path under `/var/folders/.../T/` resolved to itself cleanly |
| `unit.line` / `unit.end_line` accuracy | Assumed these are exact source line boundaries (standard for code-search tools) | Across 30 distinct hits, roughly 60% report a `line` that does not match the real `def`/`class` location found by `grep -n` in the same file; `end_line` frequently lands near the enclosing file's total line count rather than the unit's true closing brace, e.g. `add_argument` (real: line 290 of a 533-line file) reported as `line:1, end_line:533`; `parse_args` (real: 1370) reported as `line:213, end_line:3814` | `unit.code` (the verbatim snippet) was correct in every checked case even when `line`/`end_line` were wrong — only the numeric locators are unreliable, most often for methods in large classes or files with duplicate top-level names. Hypothesis: interacts with default embedding pooling (`--pool-factor 2`); untested with `--no-pool` |
| Concurrency safety | Unknown / assumed to need locking | Two simultaneous `--json` searches against the same warm index both completed with valid JSON, exit 0, no errors, ~0.94s combined wall time [`07_concurrent_a/b.stdout.txt`] | No observed lock contention or corruption for concurrent **reads**; concurrent **writes** (simultaneous cold `init`) were not tested and remain an open risk |
| Non-existent path handling | Assumed generic error | `Error: Path does not exist: …` **plus** a "Closest existing directory" suggestion and its contents listing [`03j_json_nonexistent_path.stderr.txt`] | Friendlier and more structured than a bare error — adapter can surface the suggestion directly to the calling agent |

## Contradictions & Surprises

- **`unit.line`/`unit.end_line` are unreliable for a majority of function/method hits** in this corpus (verified against `grep -n` ground truth for `add_argument`, `parse_args` (×2 distinct hits), `with_resource`/`is_bool_flag`, `FLAG_NEEDS_VALUE`) — `unit.code` remained correct in every case, so any adapter feature promising "jump to definition" or "file:line" citations from JSON output alone will point agents to the wrong line.
- **`--json --files-only` is not JSON** — it silently degrades to plain-text file paths with exit 0 and no warning, the one flag combination in the whole matrix where `--json` does not hold.
- **This machine already has a pre-existing shared colgrep project rooted at `/private/tmp`** (2434 functions, 11 searches, present *before* this probe run touched anything) that any subdirectory under `/private/tmp` silently joins. `colgrep clear` only accepts a whole-project scope (no subdirectory-level clear), so clearing our probe corpus's "project" would have deleted other concurrent sessions' indexed data sharing that same ancestor bucket — we therefore did **not** run `colgrep clear` against it (see Pointers/cleanup note).
- **`colgrep settings` prints a `k: 25 (default)`** that does not match the actual runtime default of 15 confirmed by both `--help` and probe 4 — the settings display is stale documentation, not the live default.
- **`--stats` is entirely machine-global**, not scoped to any project/path argument (it takes none) — it dumped 154 other projects' absolute paths belonging to unrelated sessions/repositories on this machine; an adapter surfacing `--stats` verbatim to an agent would leak cross-project filesystem layout.

## Steering Questions

- [now] Given `unit.line`/`unit.end_line` are frequently wrong, should the adapter drop file:line citations entirely, or add a validating post-check (re-`grep` the `signature` in `unit.file`) before presenting a location to the calling agent?
- [now] Since `colgrep clear` has no subdirectory-level scope and this machine's `/private/tmp` project is already shared across sessions, should the adapter refuse to operate on any path whose resolved `Project:` (via `colgrep status`) is shallower than the path it was given, and surface that mismatch as an error instead of indexing?
- [next run] Is the `line`/`end_line` inaccuracy correlated with `--pool-factor` (default 2)? Re-run a subset of these exact queries with `--no-pool` (or `--pool-factor 1`) against the same corpus to isolate the cause before deciding whether the adapter should always pass `--no-pool`.
- [next run] Should `--stats` ever be exposed as an MCP tool/resource given it is global and leaks other projects' paths, or should the adapter only expose the per-project `status` subcommand?
- [later] Cold-start behaviour with an empty model cache (probe 10b) could not be observed in this sandbox (HOME reassignment is blocked). Someone with an environment permitting `HOME` overrides should capture the first-run model-download shape (size, duration, offline failure mode, any consent prompt) before the adapter ships a timeout for first use.

## Pointers

- Roadmap leaf: `__roadmap__/colgrep_mcp/research_colgrep_behaviour.md`
- Architecture baseline: `__reports__/colgrep_mcp/00-architecture_v0.md` — **referenced by the leaf but absent from this worktree** at probe time; the README's own index lists it as "(latest)" despite the file not existing here. All Baseline claims above therefore cite `colgrep --help` instead; the team lead should reconcile this discrepancy and re-diff this report against the architecture report once it lands.
- Raw evidence: `__reports__/colgrep_mcp/evidence/colgrep/*.{stdout.txt,stderr.txt,exit,time}` (35 probes + 1 blocked-probe note)
- Corpus used: `git clone --depth 1 https://github.com/pallets/click.git` (152–156 Python/Markdown files) under this session's scratchpad; not committed, not part of this repository.
- Cleanup performed: the isolated single-purpose test corpus at `/var/folders/.../T/colgrep_clear_test` was `colgrep clear`-ed and confirmed removed (`06_clear.stdout.txt`, re-`status` in the same probe). The main click-corpus clone's project root resolved to the pre-existing shared `/private/tmp` bucket described above; running `colgrep clear` against it was judged unsafe (would remove other sessions' concurrently-held index data) and was deliberately **not** run — see Contradictions & Surprises. The on-disk corpus clone itself was deleted from the scratchpad instead.
