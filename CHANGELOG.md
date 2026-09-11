# Changelog

All notable changes to colgrep-mcp are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow SemVer.
`server/pyproject.toml` is the version source of truth; plugin manifests mirror it.

## [Unreleased]

## [0.1.0] - 2026-09-12

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
