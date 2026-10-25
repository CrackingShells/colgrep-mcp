# Reports — match_lines

## Round 00
- `00-observation_markdown_match_lines_v0.md` — a hit on a long markdown file shows the file's first lines: colgrep's text renderer finds the matching lines, its `--json` does not carry them, so `hit_from_raw` takes `code_lines[:snippet_lines]`; fix A in this server (match window, `match_hit_id`), B upstream (match lines in `--json`), C upstream (section-level markdown units) (latest)

## Status
Opened 2026-10-24 from the Murmuration lab's wave 8. Not started.
