"""Drift guards for the maintainer dev plugin (`dev/`) and the surface `AGENTS.md` keeps.

The repository's process knowledge lives in `dev/skills/*/SKILL.md`, loaded on
demand through the `colgrep-mcp-dev` plugin; `AGENTS.md` is meant to stay a
thin surface that only tells a cold agent the skills exist. Nothing but these
tests stops `AGENTS.md` from growing back into a manual, a skill from being
added without being announced there, or the product plugin from accidentally
shipping maintainer skills to end users (dev_plugin R01 §C1-C3).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import colgrep_mcp

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_MD = REPO_ROOT / "AGENTS.md"
DEV_PLUGIN = REPO_ROOT / "dev"
DEV_SKILLS = DEV_PLUGIN / "skills"

#: The surface file stays a pointer, not a manual (dev_plugin R01 §C3).
AGENTS_LINE_CAP = 130

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def _load(relpath: str) -> dict:
    return json.loads((REPO_ROOT / relpath).read_text())


def _skill_dirs() -> list[Path]:
    # git does not track empty directories, so a checkout with no skill yet has
    # no dev/skills/ at all; that is "zero skills", not an error.
    if not DEV_SKILLS.is_dir():
        return []
    return sorted(p for p in DEV_SKILLS.iterdir() if (p / "SKILL.md").is_file())


def _frontmatter(skill_md: Path) -> dict[str, str]:
    match = _FRONTMATTER_RE.match(skill_md.read_text())
    assert match, f"{skill_md} has no YAML front matter"
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and not line.startswith(" "):
            fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def test_agents_md_stays_under_the_line_cap():
    lines = AGENTS_MD.read_text().splitlines()
    assert len(lines) <= AGENTS_LINE_CAP, f"AGENTS.md is {len(lines)} lines; move detail into a dev skill"


def test_agents_md_names_every_dev_skill():
    text = AGENTS_MD.read_text()
    missing = [d.name for d in _skill_dirs() if f"`{d.name}`" not in text]
    assert not missing, f"AGENTS.md does not name these dev skills: {missing}"


def test_agents_md_says_how_to_load_the_dev_plugin():
    text = AGENTS_MD.read_text()
    assert "--plugin-dir ./dev" in text or "--plugin-dir dev" in text
    assert "colgrep-mcp-dev@cracking-shells" in text


def test_every_dev_skill_has_a_name_matching_its_directory_and_a_description():
    for skill_dir in _skill_dirs():
        fm = _frontmatter(skill_dir / "SKILL.md")
        assert fm.get("name") == skill_dir.name, f"{skill_dir.name}: front matter name is {fm.get('name')!r}"
        assert len(fm.get("description", "")) >= 80, f"{skill_dir.name}: description must say when to load it"


def test_dev_plugin_manifest_is_the_versioned_skills_plugin():
    manifest = _load("dev/.claude-plugin/plugin.json")
    assert manifest["name"] == "colgrep-mcp-dev"
    assert manifest["skills"] == "./skills/"
    assert manifest["version"] == colgrep_mcp.__version__
    assert "mcpServers" not in manifest, "the dev plugin carries knowledge, never a server"


def test_marketplace_lists_both_plugins_from_disjoint_sources():
    plugins = {p["name"]: p for p in _load(".claude-plugin/marketplace.json")["plugins"]}
    assert set(plugins) == {"colgrep-mcp", "colgrep-mcp-dev"}
    assert plugins["colgrep-mcp-dev"]["source"] == "./dev"
    assert plugins["colgrep-mcp"]["source"] == "./"


def test_product_plugin_never_ships_the_dev_skills():
    product_skills = (REPO_ROOT / _load(".claude-plugin/plugin.json")["skills"]).resolve()
    assert product_skills != DEV_SKILLS.resolve()
    assert DEV_SKILLS.resolve() not in product_skills.parents
    assert not product_skills.is_relative_to(DEV_PLUGIN.resolve())
