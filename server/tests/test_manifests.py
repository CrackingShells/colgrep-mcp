"""Consistency guards across the plugin packaging manifests.

Four JSON files at the repo root (plus one under `.claude-plugin/` and one
under `.codex-plugin/`) describe the same server to three different plugin
ecosystems (Claude Code, Agent Plugins 1.0, Codex). Nothing enforces that
they stay in sync on a version bump or a manifest edit except these tests.
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


def test_mcp_configs_equivalent():
    claude_mcp = _load(".mcp.json")
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
    assert claude_server["command"] == agent_server["command"]

    def normalize(args: list[str]) -> list[str]:
        return [a.replace("${CLAUDE_PLUGIN_ROOT}", "${PLUGIN_ROOT}") for a in args]

    assert normalize(claude_server["args"]) == agent_server["args"]

    for key in agent_server.get("env", {}):
        assert key not in FORBIDDEN_MCP_ENV_KEYS


def test_names_aligned():
    claude_name = _load(".claude-plugin/plugin.json")["name"]
    agent_name = _load("plugin.json")["name"]
    codex_name = _load(".codex-plugin/plugin.json")["name"]

    assert claude_name == agent_name == codex_name
