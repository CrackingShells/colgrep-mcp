# pypi_publication — reports

Fifth campaign of this repository (2026-09-12, after `dev_plugin` 0.2.0): publish `colgrep-mcp` to PyPI through trusted publishing so every manifest launches `uvx colgrep-mcp==<version>` with no root placeholder, and make the clone path first class next to it. Single-agent, no roadmap tree: five step commits on `claude/colgrep-pypi-publication-68740f`.

## Round 00
- `00-architecture_v0.md` — R01 (pypi_publication): the trigger (tag push, C1), the build guards (C2), trusted publishing (C3), the GitHub release (C4), package metadata (C5), the pinned manifests (C6), the clone path (C7); decision table D1–D9; the one-time PyPI configuration the PI does by hand.

## Status
Implemented on the branch; awaiting the PI's trusted-publisher registration on PyPI and the first `v0.3.0` tag push.
