# colgrep-mcp — Architecture Analysis (v1)

Date: 2026-09-11
Prior version: `00-architecture_v0.md` — this revision is a **delta**: everything in v0 stands except the items below, which R02 (MCP feature matrix) and R03 (measured colgrep behaviour) forced.

## Deltas driven by R03 (colgrep 1.6.2 measured)

| # | Finding [source] | v0 assumption | v1 contract |
|:--|:--|:--|:--|
| D1 | `unit.line` is 1 and `unit.end_line` is the file's line count for every unit that is not the first in its file; `unit.code` is always verbatim-correct [R03 Contradictions; lead re-verified on `server/colgrep_mcp`: `Doctor` reported 1-105, real 98] | JSON `line`/`end_line` are trustworthy and become `hit_id` | The adapter **locates** each unit: `locate_unit(file_text, code, reported_line, reported_end) -> (line, end_line, verified: bool)` finds the first line of `code` in the file (exact line match; disambiguate multiple candidates by matching the following lines; if `code` has one line, prefer the candidate nearest `reported_line`), sets `end_line = line + len(code_lines) - 1`, `verified=True`. On failure fall back to reported values with `verified=False`. `SearchHit` gains `location_verified: bool`. File contents are read once per file per search call (small dict cache). `hit_id` is built from the located lines. |
| D2 | Indexing emits no per-file progress: stderr is only `🤖 Model: …`, `📂 Building index...`, then one summary line `Indexed <root> (subdir: …) (added: N, changed: N, deleted: N, unchanged: N)` or `Index is up to date for <root> (N files)` [R03 probes 1, 2a] | `parse_progress` extracts `n/total` | `parse_progress` parses the **summary** line into counts; a `_ProgressForwarder` in `index_build` sends an **indeterminate heartbeat** `ctx.report_progress(elapsed_s, total=None, message="indexing … (Ns)")` every 5 s while the subprocess runs (keeps the client alive — R02: Claude Code aborts idle calls), then a final `report_progress(1, total=1, message=<summary line>)`. `IndexBuildResult` gains `added/changed/deleted/unchanged: int | None` and `up_to_date: bool`. |
| D3 | colgrep folds a path into the nearest **already-registered ancestor project** (e.g. anything under `/private/tmp` joined a pre-existing `/private/tmp` project); `colgrep clear` has whole-project scope only [R03 Observations] | project == requested path | `IndexStatus` gains `requested_path: str` beside `project` (the root colgrep reports). `index_clear` first runs `status(path)`; if `project != requested_path` it raises `ToolError` explaining that clearing would delete the index for `<project>` covering other directories, and that the caller must pass `path=<project>` explicitly (plus `confirm`/elicitation). The e2e corpus must live **outside** `/private/tmp` (use `~/colgrep-e2e-corpus/`). |
| D4 | `--json --files-only` prints plain text [R03 probe 3d] | — | Confirms v0: `find_files` derives files from `--json` hits itself; the adapter never passes `-l`. |
| D5 | `-k` omitted → exactly 15 hits for a pure semantic query, but 95 (uncapped) when `-e` is present [R03 probes 4, 4b] | `limit=None` ⇒ exhaustive | `limit=None` omits `-k`; exhaustive **only when `pattern` is set**. When `limit is None and pattern is None` the tool appends `notes=["limit omitted without pattern: colgrep applies its own default of 15; pass a larger limit for more"]`. Guide and SKILL wording updated accordingly (leaf `docs_readme` carries the fix into `guide.md`/`SKILL.md`). |
| D6 | Zero hits → stdout `[]`, exit 0; bad path → exit 1, stderr `Error: Path does not exist: … Closest existing directory: … Contents: …` [R03 probes 3i, 3j] | — | Confirms v0 error model; the bad-path `ToolError` includes colgrep's "closest existing directory" hint verbatim. |
| D7 | Search stderr carries `🤖 Model…`/`📂 Building index...` only when the index was (re)built [R03 probes 3a vs 3b] | `index_updated` unspecified | `SearchResult.index_updated = "Building index" in stderr`. |
| D8 | `--content`/`-n` are no-ops under `--json`; `code` is always full [R03 probes 3b/3c] | — | Adapter never passes `-c`/`-n`; `snippet_lines` is applied server-side (v0 already did this). |
| D9 | `--stats` is machine-global (154 projects here) [R03] | — | Kept (`list_indexes`): the server is local to the machine owner. README notes it. |
| D10 | `colgrep clear` does not prompt [R03 probe 6] | might prompt | Adapter passes no stdin; nothing to suppress. |
| D11 | `colgrep settings` shows `k: 25 (default)` while runtime default is 15 [R03] | — | `colgrep://settings` is served raw; the guide states the runtime default is 15. |

## Deltas driven by R02 (MCP feature matrix)

| # | Finding | v1 contract |
|:--|:--|:--|
| M1 | Roots deprecated (2026-07-28); Claude Code answers `roots/list` today | v0 already made roots the third fallback; keep, wrapped in `try/except Exception` and `warnings.catch_warnings()`; never required. |
| M2 | Server-initiated logging (`notifications/message`) deprecated in 2026-07-28 | `ctx.info/warning` calls stay but are wrapped in a helper `safe_log(ctx, level, msg)` that swallows any exception; tool results never depend on logs. |
| M3 | Elicitation form mode adopt-guarded; capability check via `ctx.session.check_client_capability(ClientCapabilities(elicitation=ElicitationCapability()))` | As v0. |
| M4 | `instructions` disappears in the 2026-07-28 handshake redesign | Every tool description is self-sufficient; `instructions` duplicates, never replaces, tool-level guidance. |
| M5 | Icons defer, completions defer/adopt-guarded, subscriptions reject | Icons dropped from v0.1. Completions **kept** (cheap, already specced, harmless if unused). `notify_resource_updated` kept as fire-and-forget guarded call. |

## Updated models (delta only)

```python
class SearchHit(BaseModel):   # + field
    location_verified: bool

class IndexStatus(BaseModel): # + field
    requested_path: str

class IndexBuildResult(BaseModel):  # + fields
    added: int | None; changed: int | None; deleted: int | None; unchanged: int | None
    up_to_date: bool = False
```

## Risk register update

| # | Risk | Change |
|:--|:--|:--|
| 1 | Cold index vs client timeout | Mitigated by D2 heartbeat; cold click corpus measured at 15 s on CPU, so v0.1 default timeout 600 s is ample. |
| 8 (new) | `locate_unit` mismatch on files edited after indexing | `verified=False` + reported fallback; `expand` still reads whatever is at those lines and says so. |
| 9 (new) | Clearing a shared ancestor project | D3 refusal + explicit root path. |
