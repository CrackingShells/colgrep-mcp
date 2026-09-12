"""Consistency guards across the plugin packaging manifests.

`plugin.json` and `mcp.json` at the repo root, `.claude-plugin/plugin.json`
plus `.claude-plugin/mcp.json`, and `.codex-plugin/plugin.json` describe the
same server to three different plugin ecosystems (Claude Code, Agent
Plugins 1.0, Codex). Nothing enforces that they stay in sync on a version
bump or a manifest edit except these tests.

The Claude Code manifest lives at `.claude-plugin/mcp.json`, not at a
root-level `.mcp.json`: Claude Code's project-scope MCP auto-discovery only
ever looks for a root `.mcp.json`, and this repository is itself sometimes
opened as a plain project rather than loaded as a plugin. A root `.mcp.json`
using `${CLAUDE_PLUGIN_ROOT}` broke exactly that way (spawn ENOENT, see
__reports__/repo_health/00-findings_launch_placeholders_v0.md); relocating
the file makes it invisible to project-scope auto-discovery.
"""

from __future__ import annotations

import json
from pathlib import Path

import colgrep_mcp

# server/tests/test_manifests.py -> parents[0]=tests, [1]=server, [2]=repo root
REPO_ROOT = Path(__file__).resolve().parents[2]

AGENT_PLUGIN_PERMITTED_FIELDS = {
    "$schema",
    "name",
    "version",
    "description",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
    "extensions",
}

FORBIDDEN_MCP_ENV_KEYS = {"PLUGIN_ROOT", "PLUGIN_DATA"}


def _load(relpath: str) -> dict:
    return json.loads((REPO_ROOT / relpath).read_text())


def _schema_version(schema_url: str) -> str:
    # https://agent-plugins.org/schemas/<version>/<name>.schema.json
    return schema_url.rstrip("/").split("/")[-2]


def test_versions_aligned():
    version = colgrep_mcp.__version__

    assert _load(".claude-plugin/plugin.json")["version"] == version
    assert _load("plugin.json")["version"] == version
    assert _load(".codex-plugin/plugin.json")["version"] == version


def test_agent_plugin_fields_whitelist():
    manifest = _load("plugin.json")

    assert set(manifest) <= AGENT_PLUGIN_PERMITTED_FIELDS
    assert (
        manifest["$schema"]
        == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    )


def _launch_args(args: list[str]) -> None:
    """Every manifest launches with the same cross-platform argv shape.

    `uv run --quiet --directory <ROOT-placeholder>/server colgrep-mcp`, with
    the ecosystem's own root placeholder only in `args` — never in
    `command`, per the Agent Plugins 1.0 spec (`command` forbids placeholder
    expansion) and to keep a bare, always-resolvable executable name for
    every context Claude Code's `.mcp.json` can be loaded from.
    """
    assert args[:2] == ["run", "--quiet"]
    assert args[-3:] == ["--directory", args[-2], "colgrep-mcp"]
    assert args[-2].endswith("/server")


def test_mcp_configs_equivalent():
    claude_mcp = _load(".claude-plugin/mcp.json")
    agent_mcp = _load("mcp.json")
    agent_plugin = _load("plugin.json")

    assert (
        agent_mcp["$schema"] == "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
    )
    assert _schema_version(agent_mcp["$schema"]) == _schema_version(
        agent_plugin["$schema"]
    )

    claude_server = claude_mcp["mcpServers"]["colgrep"]
    agent_server = agent_mcp["mcpServers"]["colgrep"]

    assert agent_server["type"] == "stdio"

    # `command` must be a bare executable name in every ecosystem: no
    # placeholder, ever (Agent Plugins 1.0 spec §7.2.1 forbids it outright;
    # Claude Code's plugin-substitution mechanism is undocumented for the
    # `${VAR:-default}` fallback that would make a placeholder safe there too).
    assert claude_server["command"] == "uv"
    assert agent_server["command"] == "uv"
    assert "$" not in claude_server["command"]
    assert "$" not in agent_server["command"]

    _launch_args(claude_server["args"])
    _launch_args(agent_server["args"])
    # Only the ecosystem's own root placeholder differs.
    assert claude_server["args"][-2] == "${CLAUDE_PLUGIN_ROOT}/server"
    assert agent_server["args"][-2] == "${PLUGIN_ROOT}/server"

    for key in agent_server.get("env", {}):
        assert key not in FORBIDDEN_MCP_ENV_KEYS


def test_names_aligned():
    claude_name = _load(".claude-plugin/plugin.json")["name"]
    agent_name = _load("plugin.json")["name"]
    codex_name = _load(".codex-plugin/plugin.json")["name"]

    assert claude_name == agent_name == codex_name
