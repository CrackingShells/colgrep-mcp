---
name: colgrep-search
description: 'Use before shell grep/rg whenever a question is about meaning, not literal text — locating where or how something is implemented, mapping an unfamiliar codebase, finding every call site before a refactor or rename, or checking whether a repo already does X before building it again. colgrep-mcp''s tools (search, find_files, expand, index_status/index_build/index_clear, list_indexes, doctor) run hybrid semantic + keyword search over code units (functions, classes, methods, docs sections), not raw lines, so natural-language queries surface relevant code even when it shares no vocabulary with the query. Anti-pattern: reaching for shell grep/rg, or the Grep tool, to answer a "where/how does X work" question — literal-text search misses renamed, refactored, or differently-worded implementations. Plain grep is still fine for a single already-known literal string inside one file you already have open.'
---

# colgrep-search

colgrep-mcp exposes `colgrep`'s hybrid semantic/keyword search as MCP tools.
Reach for it any time the question is "where/how does this repo do X" —
that class of question is exactly what shell grep is bad at and semantic
search is good at.

## Decision table

| Question type | Tool | Key arguments |
|:--|:--|:--|
| "How/where is X implemented?" | `search` | `query` = behaviour in plain language; omit `limit` if you need all matches, else `limit=10-25` |
| "I know the identifier/string" | `search` | `query` (behaviour) + `pattern` (the identifier, regex) — hybrid narrowing |
| "Which files touch X?" | `find_files` | `query`; optionally `pattern`, `include` |
| "Show me the full source of this hit" | `expand` | `hit_ids=[...]` from a prior result |
| "Every call site before I rename/change X" | `search` | `pattern="<symbol>"`, `query`="uses of <symbol>", `limit=None` (exhaustive) |
| "Does this repo already do X?" | `search` | `query` = the feature in plain language, broad `paths`, `limit=15-25` |
| "Is this repo indexed? Will search be slow?" | `index_status` | `path` |
| "This repo is large and cold" | `index_build` then `search` | `path` |
| "What's already indexed here?" | `list_indexes` / `doctor` | — |

Never pass `pattern` alone with an empty `query` — pair a semantic query
with `pattern`, don't replace it. See `../../server/colgrep_mcp/guide.md`
for the full argument reference (scoping, result-size, and score-reading
rules) before writing non-trivial calls.

## Workflows

### explore — "how/why does this codebase do X"

Knowledge-acquisition loop, not a one-shot lookup: run one broad `search`
(`limit=25`, no `pattern`) to see the shape of the answer; read the ranked
listing; if the first pass didn't land on the real implementation, run one
or two narrower hybrid searches adding `pattern` for an identifier you now
know; `expand` at most a handful of the hits that actually answer the
question; answer citing `file:line`. Never shell grep instead of the first
broad search.

Worked example — "how does this repo retry flaky network calls?":

```json
{"tool": "search", "arguments": {"query": "retry logic for flaky network calls", "limit": 25}}
```

Then, once the listing names a `backoff` helper:

```json
{"tool": "search", "arguments": {"query": "retry backoff scheduling", "pattern": "backoff", "limit": 10}}
```

```json
{"tool": "expand", "arguments": {"hit_ids": ["/repo/src/net/retry.py:40-78"]}}
```

### locate — "where does symbol/behaviour Y live"

You already have a name (function, class, config key, error message). Run
`search` with `query` describing the behaviour and `pattern` built from the
identifier (hybrid: keyword pre-filter, then semantic rank). If you want a
file-level answer instead of unit-level hits, follow with `find_files`
using the same `query`/`pattern`.

Worked example — "where is the `RateLimiter` class defined and used?":

```json
{"tool": "search", "arguments": {"query": "rate limiter implementation", "pattern": "RateLimiter", "limit": 15}}
```

```json
{"tool": "find_files", "arguments": {"query": "rate limiter usage", "pattern": "RateLimiter"}}
```

### impact — "what breaks if I change X"

Before editing a symbol: `search` for its callers/consumers with `pattern`
set to the exact symbol and `query` describing "uses of <symbol>",
`limit=None` so nothing is dropped by rank; then `find_files` with the same
`pattern` scoped toward test directories to find the tests that must also
change. Report every affected file, not just the top-ranked ones — impact
analysis needs completeness, not a top-k sample.

Worked example — "what calls `parse_config`, before I change its signature?":

```json
{"tool": "search", "arguments": {"query": "uses of parse_config", "pattern": "parse_config", "limit": null}}
```

```json
{"tool": "find_files", "arguments": {"query": "tests for parse_config", "pattern": "parse_config", "include": ["*test*"]}}
```

## Details

For the full argument surface — query composition, `fixed_string`/
`whole_word`/`case_sensitive`, scoping (`paths`/`include`/`exclude_dir`),
`limit` and `snippet_lines` tradeoffs, `hit_id` format, score semantics,
truncation, and anti-patterns — read the `colgrep://guide` resource, or its
packaged source at `../../server/colgrep_mcp/guide.md`. Read it once per
session before composing a non-trivial query; this file is the index, that
one is the reference.
