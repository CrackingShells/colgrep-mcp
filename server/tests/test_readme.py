"""Drift test for the two READMEs (`build/tools/integrate/docs_readme`).

Each README's Tools table is written by hand once from `list_tools()` and is
not regenerated automatically, so nothing stops it from rotting the moment a
tool is renamed, added, or removed. This test parses the `### Tools` section
(row shape `| \\`name\\` | one-line purpose |`) and asserts the set of names it
lists is exactly the set the live server reports, through the same
in-memory `Client(build())` every other end-to-end test in this suite uses.
The repository README is the landing page; `server/README.md` is the PyPI
page (pypi_publication R01 §C5) and carries the same table.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from mcp import Client

from colgrep_mcp.server import build

pytestmark = pytest.mark.anyio

# server/tests/test_readme.py -> server -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
READMES = (REPO_ROOT / "README.md", REPO_ROOT / "server" / "README.md")

# Matches a markdown table row whose first cell is a single backtick-quoted
# token, e.g. `| \`search\` | Ranked semantic ... \`hit_id\`s. |` captures
# "search" — anchored at the row start so a backtick-quoted word later in the
# Purpose column (like `hit_id`) is never mistaken for the row's tool name.
_ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|", re.MULTILINE)

_SECTION_HEADING = "### Tools"


def _readme_tool_names(readme: Path) -> set[str]:
    r"""Tool names named by the README's `### Tools` table, by heading name only.

    Scoped to that one section (up to the next `##`/`###` heading) so the
    Resources and Configuration tables below it — which use the same
    `| \`token\` | ... |` row shape for URIs and env var names — are never
    swept in.
    """
    text = readme.read_text()
    start = text.index(_SECTION_HEADING)
    rest = text[start + len(_SECTION_HEADING) :]
    next_heading = re.search(r"^#{2,3} ", rest, re.MULTILINE)
    section = rest[: next_heading.start()] if next_heading else rest
    return set(_ROW_RE.findall(section))


@pytest.mark.parametrize("readme", READMES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
async def test_tools_table_matches_server(readme: Path):
    readme_names = _readme_tool_names(readme)
    assert readme_names, (
        f"no tool rows parsed under {_SECTION_HEADING!r} in {readme.name} -- did the section move or get renamed?"
    )

    async with Client(build(), raise_exceptions=True) as client:
        live_names = {tool.name for tool in (await client.list_tools()).tools}

    assert readme_names == live_names
