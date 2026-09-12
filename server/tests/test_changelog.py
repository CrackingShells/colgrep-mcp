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
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHANGELOG = REPO_ROOT / "CHANGELOG.md"

_HEADING_RE = re.compile(r"^## (?:Unreleased|v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.]+)? \(\d{4}-\d{2}-\d{2}\))$")


def test_version_headings_use_the_commitizen_shape():
    headings = [line for line in CHANGELOG.read_text().splitlines() if line.startswith("## ")]
    assert headings, "CHANGELOG.md has no `## ` version headings"
    bad = [h for h in headings if not _HEADING_RE.match(h)]
    assert not bad, f"headings commitizen's incremental mode cannot parse: {bad}"
