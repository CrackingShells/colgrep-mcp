"""Drift guard for the CHANGELOG heading format commitizen's incremental mode parses.

`cz bump` (see `[tool.commitizen]` in pyproject.toml) prepends a section for the
new version and, in incremental mode, finds where the previous one starts by
matching its own heading shape, `## vX.Y.Z (YYYY-MM-DD)`, plus `## Unreleased`.
A hand-edited heading in any other shape (the Keep-a-Changelog `## [X.Y.Z] - date`
this file originally used) is invisible to it, and the next bump silently
prepends a duplicate history. Measured on 2026-09-12 with commitizen 4.18.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHANGELOG = REPO_ROOT / "CHANGELOG.md"

_HEADING_RE = re.compile(r"^## (?:Unreleased|v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.]+)? \(\d{4}-\d{2}-\d{2}\))$")


def test_version_headings_use_the_commitizen_shape():
    headings = [line for line in CHANGELOG.read_text().splitlines() if line.startswith("## ")]
    assert headings, "CHANGELOG.md has no `## ` version headings"
    bad = [h for h in headings if not _HEADING_RE.match(h)]
    assert not bad, f"headings commitizen's incremental mode cannot parse: {bad}"


def test_changelog_pattern_skips_merge_subjects_and_keeps_step_subjects():
    """`gh pr merge --subject "<step subject> (PR #N)"` makes the merge commit repeat
    the step's subject; both matched `changelog_pattern` and every release since
    v0.3.0 listed the entry twice. commitizen applies the pattern with `re.match`
    to the *whole* message, body included (`changelog.generate_tree_from_commits`,
    probed on commitizen 4.18), so the messages here carry a body: a pattern that
    anchors the suffix with `$` passes the subject-only form and still lists the
    merge twice. Regression test: the `(PR #N)` cases fail against the pattern
    that shipped in v0.4.0 and against that `$`-anchored first attempt."""
    config = tomllib.loads((REPO_ROOT / "server" / "pyproject.toml").read_text())
    pattern = re.compile(config["tool"]["commitizen"]["customize"]["changelog_pattern"])
    body = "\n\nWhy the change exists.\n\nCo-Authored-By: someone <x@y>"

    kept = [
        "feat(plugin): ship the search policy, grep redirect and worktree reap as plugin hooks",
        "fix(plugin): treat the system temp directory and appdata as machine state in the hook gate",
        "perf(search): skip the per-lock resolve",
        "feat(search)!: rename limit",
    ]
    skipped = [
        "feat(plugin): ship the search policy, grep redirect and worktree reap as plugin hooks (PR #7)",
        "fix(repo): replace local machine paths (PR #12)",
        "docs(reports): close the harness_wiring reports index after the v0.4.0 release",
        "refactor(index): split the renderer",
    ]
    for message in (*kept, *(s + body for s in kept)):
        assert pattern.match(message), message
    for message in (*skipped, *(s + body for s in skipped)):
        assert not pattern.match(message), message
