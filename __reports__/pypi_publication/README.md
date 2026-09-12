# pypi_publication — reports

Fifth campaign of this repository (2026-09-12, after `dev_plugin` 0.2.0): publish `colgrep-mcp` to PyPI through trusted publishing so every manifest launches `uvx colgrep-mcp==<version>` with no root placeholder, and make the clone path first class next to it. Single-agent, no roadmap tree: five step commits on `claude/colgrep-pypi-publication-68740f`.

## Round 00
- `00-architecture_v0.md` — R01 (pypi_publication): the trigger (tag push, C1), the build guards (C2), trusted publishing (C3), the GitHub release (C4), package metadata (C5), the pinned manifests (C6), the clone path (C7); decision table D1–D9; the one-time PyPI configuration the PI does by hand.

## Status
Closed. Landed as PR #6 and released as v0.3.0 from the main checkout on 2026-09-13; `publish.yml` run 34722006472 uploaded `colgrep_mcp-0.3.0-py3-none-any.whl` and `.tar.gz` to PyPI with attestations and created the GitHub release. Verified from the release machine: `uvx colgrep-mcp==0.3.0 --version` prints 0.3.0 and `claude --plugin-dir . mcp list` shows the manifest connected.

Next-cycle items (no retrospective report for a single-agent cycle; recorded in the skills instead): `gh pr merge --subject` needs `--body` or GitHub copies the PR title into the merge body and commitizen lists it twice in the changelog (`landing-and-release/references/landing-a-pr.md`); a venv created before the repository moved keeps absolute shebangs and `uv run` reports "Failed to spawn" (`stack-traps/references/machine.md#stale-venv`).
