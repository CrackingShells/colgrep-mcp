---
type: findings
topic: index_housekeeping
date: 2026-09-13
version: v0
prior-version: none
---

# Does `colgrep clear` remove the index of a path that no longer exists? (v0)

Report id `R02` (index_housekeeping). Probe run on 2026-09-13, macOS, colgrep
1.6.2, on one orphaned index whose `project_path` had no indexed ancestor
(so a folding clear could not have reached another project either way).

## Result

**No.** `colgrep clear <gone path>` exits 1 without touching the store. Prune
must remove the index directory itself (R01 D1, C5). The retired machine
hook's comment ("clear merely errors when the directory no longer exists")
is confirmed.

## Method

1. Survey the store read-only (`project.json` per index directory; a path is
   orphaned when `os.path.exists(project_path)` is false): 165 indexes, 65
   orphaned.
2. Pick the smallest orphan with **no indexed ancestor** — the orphan first
   chosen (`__canons__` under a removed worktree) was rejected because its
   parent worktree was itself indexed, which would have made the probe
   ambiguous.
3. Run `status` then `clear` on the gone path; check the directory after.

## Transcript

Paths are the maintainer's, shown with the `/Users/me` placeholder.

```text
$ colgrep status "/Users/me/src/explore/colgrep_mcp/server/colgrep_mcp" --color never
Error: No such file or directory (os error 2)
exit=1

$ colgrep clear "/Users/me/src/explore/colgrep_mcp/server/colgrep_mcp" --color never
Error: No such file or directory (os error 2)
exit=1

$ ls "~/Library/Application Support/colgrep/indices/colgrep_mcp-a1887fc5"
index project.json state.json
$ ls "~/Library/Application Support/colgrep/indices" | wc -l
165
```

## Store facts confirmed on the way

| Fact | Value |
|:--|:--|
| Index directory layout | `<store>/<project_name>-<8 hex>/{project.json, state.json, index/, .lock}` |
| `project.json` | `{"project_path", "project_name", "model"}` — no timestamps |
| `state.json` | `{"cli_version", "index_format_version", "files": {rel: {content_hash, mtime, size}}, "ignored_files", "search_count", "dirty"}` |
| `state.json` mtime vs directory mtime | identical to the second on every sampled index, including the three searched during this session — `state.json` is rewritten on each search |
| Size pass (`os.scandir`, all 165) | 15 ms median of 5 |
| `project.json` + `state.json` read pass | 25 ms |
| Indexed pairs where one project is a strict descendant of another | 130 |
| Orphaned indexes | 65 of 165 |

## Steering

- Prune deletes `<store>/<dir>` directly, guarded by that directory's own
  `project.json` (R01 C5). Confirmed necessary, not just preferable.
- `status` also fails on a gone path, so the store root must be derived from
  a `status` call on a project that *exists* (R01 C1).
