# Changelog

All notable changes to colgrep-mcp are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow SemVer.
`server/pyproject.toml` is the version source of truth; `cz bump` (see `CONTRIBUTING.md`)
writes each new section below and mirrors the version into the plugin manifests.

## v0.3.1 (2026-09-13)

### Fixed

- **repo**: replace local machine paths in fixtures, reports, roadmaps and skills with placeholders

## v0.3.0 (2026-09-13)

### Added

- **plugin**: publish colgrep-mcp to PyPI and launch it with uvx from every manifest (PR #6)
- **plugin**: publish colgrep-mcp to PyPI and launch it with uvx from every manifest
- **plugin**: launch uvx colgrep-mcp pinned to the plugin version from every manifest

## v0.2.0 (2026-09-12)

### Added

- **plugin**: add the colgrep-mcp-dev skills plugin and land the consistency follow-ups (PR #5)

### Changed

- **search**: integrate the search_path leaf (FileHit fold, one summary notification)
- **search**: send one summary log notification per search instead of one per stderr line
- **search**: fold find_files raw hits straight into FileHit without building SearchHits

### Fixed

- **skill**: probe the merge subject with cz check before land_branch.sh merges
- **index**: integrate the list_indexes text budget (leaf list_indexes_budget)
- **index**: cap list_indexes text at the text budget like every other renderer

## v0.1.2 (2026-09-12)

### Changed

- **server**: ship tool descriptions dedented through one registration helper
- **search**: skip file reads in find_files and read only the requested span in expand

### Fixed

- **server**: convert client root URIs to paths with url2pathname
- **server**: scope the ctx-less app handle to its lifespan with a ContextVar
- **resources**: keep a drive-rooted windows status path absolute

## v0.1.1 (2026-09-12)

### Fixed

- **repo**: apply the confirmed reviewer findings before the 0.1.1 release
- **plugin**: launch the server with uv run from every manifest so it works without a POSIX shell

## v0.1.0 (2026-09-12)

First release: colgrep as an MCP server, packaged as a Claude Code plugin, an Agent Plugins 1.0 plugin and a Codex plugin.

### Added
- **adapter**: parse colgrep status, stats and settings text into typed models
- **adapter**: add bounded async subprocess runner and search argv builder
- **adapter**: implement search, status, stats, settings, init and clear
- **search**: add path resolution, hit conversion and budgeted text rendering
- **resources**: expose guide, settings, indexes and per-path status resources
- **prompts**: add explore, locate and impact prompts with path completions
- **index**: add index_status, list_indexes and doctor tools
- **index**: add index_build with streamed progress and elicitation-guarded index_clear
- **search**: register search, find_files and expand tools with budgeted output
- **server**: add coded errors and hints that steer agents to the next search pattern

### Changed
- **server**: own the adapter in the lifespan and add shared path, lock and log helpers
- **search**: read source files off the event loop
- **adapter**: raise explicit errors instead of asserts for path invariants

### Fixed
- **adapter**: kill the colgrep subprocess when a tool call is cancelled
- **index**: cancel the build task and hold the lock until it ends on cancellation
- **adapter**: verify full unit blocks and tolerate trailing whitespace in locate_unit
- **search**: keep rendered text under the budget in the header-only corner case
- **search**: lock every project a multi-path search touches
- **index**: tell elicitation failure apart from a user decline in index_clear
- **server**: fail fast with a readable message on malformed environment values
- **search**: validate limit, alpha, snippet_lines and max_lines bounds
- **search**: normalise hit files to absolute paths before building hit_id
