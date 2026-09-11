# colgrep-mcp: agent guide

Served at `colgrep://guide`. Read this before your first `search` call in a
new session; skim it again if a result looks wrong.

## What colgrep indexes

colgrep indexes **code units**, not lines: functions, methods, classes,
markdown sections, and plain-text blocks. A hit is one unit, never an
arbitrary line range you picked. 18+ languages plus Markdown and plain text.
A unit's `code`/`snippet` is that unit's full extracted body — expect
complete functions and classes, not fragments.

Search is **hybrid** by default: keyword match (FTS5 full-text) and semantic
match (ColBERT late-interaction embeddings) are fused into one ranked list.
`semantic_only=true` disables the keyword half; `alpha` (0.0 keyword ...
1.0 semantic, default 0.60) tunes the blend. You will rarely need either —
the default fusion is what makes natural-language queries find code that
doesn't share vocabulary with the query.

## Choosing a tool

- `search` — ranked hits with snippets. Default choice for "where/how does
  this work" questions.
- `find_files` — which *files* are about a topic, deduplicated and ranked.
  Use when you want a file list, not per-unit hits (e.g. scoping a refactor,
  picking which files to open).
- `expand` — full source for specific `hit_id`s already returned by `search`
  or `find_files`. Use this instead of opening a file after a search.
- `index_status` — is this path indexed, with what model, how many units.
  Call before a first search on a repo you suspect is large and cold.
- `index_build` — build/refresh the index now, with streamed progress. Call
  this first on a large, never-indexed repository rather than letting a
  plain `search` eat the build cost inside its own timeout.
- `index_clear` — delete a project's index. Destructive; pass `confirm=true`
  or expect an elicitation prompt.
- `list_indexes` — every indexed project on this machine, with sizes.
- `doctor` — environment self-check (binary found, version, default root).
  Use when a tool call fails for an unclear reason.

## Writing queries

`query` is natural language describing **behaviour**, not identifiers:
"retry logic for flaky network calls", not `retry`. Semantic ranking works
on meaning; keyword vocabulary matching is the `pattern` argument's job.

Add `pattern` (a regex) when you already know an identifier, literal string,
or shape to require — it pre-filters candidates with a regex match, *then*
ranks the survivors semantically. This is hybrid narrowing: pair a semantic
`query` with `pattern` rather than passing `pattern` alone with no `query`.
Example: `query="where retries are scheduled", pattern="backoff"`.

- `fixed_string=true` — treat `pattern` as a literal substring, not regex.
  Use for strings containing regex metacharacters (`(`, `.`, `[`, `$`, ...).
- `whole_word=true` — match `pattern` on word boundaries only.
- `case_sensitive=true` — `pattern` matching is case-insensitive by default;
  set this to match case exactly.

## Scoping

- `paths` — restrict to specific files or directories instead of the whole
  project.
- `include` — glob file filters, e.g. `["*.py", "*.rs"]`.
- `exclude` — glob file exclusions.
- `exclude_dir` — directory names or globs to skip, e.g.
  `["node_modules", "vendor", "**/test_*"]`.
- `code_only=true` — skip markdown/text/config units, code only.

## Result size

`limit` caps the number of ranked **units** returned, not lines:

- Omit `limit` (`None`) for an exhaustive result set — nothing is dropped
  by rank. This is the right default when you need every match, e.g.
  enumerating all call sites before a rename.
- Pass `limit=10` to `25` while exploring a broad question, where you only
  want the top hits and will `expand` the ones that matter.
- A larger `limit` does not cost you accuracy — hits are score-ranked, so a
  smaller `limit` just truncates the tail.

`snippet_lines` (default 6) controls how many lines of each unit's body ride
along in the compact listing. Raise it if snippets are cutting off the part
you need to judge relevance; otherwise leave it and `expand` instead.

`include_code` is `false` by default — hits carry a short `snippet`, not the
full unit body. Set it `true` only when you need full code for every hit in
one call; normally call `expand` on the handful of `hit_id`s worth reading
in full, so you don't pull whole-file-sized payloads for hits you'll discard.

## Reading results

Every hit has a `hit_id`: `"<absolute file>:<line>-<end_line>"`. It is
self-describing — no server-side cache, no session state — and is exactly
what `expand(hit_ids=[...])` expects. Copy `hit_id`s straight from a result
into `expand`.

`score` is **relative within one query's result set only**. Do not compare
scores across two different `search` calls, and do not treat a score as a
confidence percentage — it ranks candidates against each other, nothing
more.

A result carries `truncated=true` when either colgrep or the server's text
budget dropped hits from the compact text listing. `structured_content`
still carries every hit's metadata even when the text was cut; when you see
`truncated=true` and need more, call `expand` on the `hit_id`s you have, or
re-run with a larger or omitted `limit` rather than assuming those were the
only matches.

Zero hits is not an error: an empty `hits` list with a note suggesting you
drop `pattern`/`include` or rephrase the query. Don't retry the identical
call expecting a different answer — change the query, drop a filter, or
widen `paths`.

## Anti-patterns

- Do not shell out to `grep`/`rg` for a question about what code does or
  where a behaviour lives — that is exactly what `search` replaces. Shell
  grep is fine for a single already-known literal in one file you have
  open; it is the wrong tool for a meaning-based question over a project.
- Do not open a whole file to read one hit — call `expand` on its `hit_id`.
- Do not re-run the same `search` call expecting new results; change the
  query, `pattern`, or scoping instead.
- Do not pass a small `limit` when you need completeness (e.g. every caller
  before a rename) — omit it.
- Do not skip `index_status`/`index_build` on a repository you know is large
  and has never been searched, then be surprised a `search` call times out.
