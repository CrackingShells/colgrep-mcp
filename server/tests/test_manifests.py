"""Consistency guards across the plugin packaging manifests.

`plugin.json` and `mcp.json` at the repo root, `.claude-plugin/plugin.json`
plus `.claude-plugin/mcp.json`, and `.codex-plugin/plugin.json` plus
`.codex-plugin/mcp.json` describe the same server to three different plugin
ecosystems (Claude Code, Agent Plugins 1.0, Codex). Nothing enforces that
they stay in sync on a version bump or a manifest edit except these tests.

Every MCP manifest launches `uvx colgrep-mcp==<version>` from PyPI: no root
placeholder anywhere in `args`, because a client that leaves
`${CLAUDE_PLUGIN_ROOT}`/`${PLUGIN_ROOT}` literal never started the server
(pypi_publication R01 §C6; the per-ecosystem placeholder rules are in
repo_health `00-findings_launch_placeholders_v0.md`). The pin equals the
package version so that a plugin update moves uvx's cache key (R01 D4).

The Claude Code manifest lives at `.claude-plugin/mcp.json`, not at a
root-level `.mcp.json`: Claude Code's project-scope MCP auto-discovery only
ever looks for a root `.mcp.json`, and this repository is itself sometimes
opened as a plain project rather than loaded as a plugin. Codex has its own
`.codex-plugin/mcp.json` so that the only placeholder left — Claude Code's
`COLGREP_MCP_ROOT=${CLAUDE_PROJECT_DIR}` in `env` — is read only by the
client documented to expand it.
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

MCP_MANIFESTS = (".claude-plugin/mcp.json", ".codex-plugin/mcp.json", "mcp.json")


def _load(relpath: str) -> dict:
    return json.loads((REPO_ROOT / relpath).read_text())


def _schema_version(schema_url: str) -> str:
    # https://agent-plugins.org/schemas/<version>/<name>.schema.json
    return schema_url.rstrip("/").split("/")[-2]


def _server(relpath: str) -> dict:
    return _load(relpath)["mcpServers"]["colgrep"]


def test_versions_aligned():
    version = colgrep_mcp.__version__

    assert _load(".claude-plugin/plugin.json")["version"] == version
    assert _load("plugin.json")["version"] == version
    assert _load(".codex-plugin/plugin.json")["version"] == version
    # The dev plugin is versioned with the product: its skills describe how to
    # maintain *this* repository at *this* version, so one `cz bump` moves both.
    assert _load("dev/.claude-plugin/plugin.json")["version"] == version


def test_agent_plugin_fields_whitelist():
    manifest = _load("plugin.json")

    assert set(manifest) <= AGENT_PLUGIN_PERMITTED_FIELDS
    assert manifest["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"


def test_every_mcp_manifest_launches_the_pinned_pypi_release():
    """`uvx colgrep-mcp==<version>`: a bare executable in `command`, one
    requirement in `args`, nothing to expand."""
    version = colgrep_mcp.__version__
    for relpath in MCP_MANIFESTS:
        server = _server(relpath)
        assert server["command"] == "uvx", relpath
        assert server["args"] == [f"colgrep-mcp=={version}"], relpath
        assert not any("$" in arg for arg in server["args"]), relpath


def test_plugin_manifests_point_at_their_own_mcp_file():
    assert _load(".claude-plugin/plugin.json")["mcpServers"] == "./.claude-plugin/mcp.json"
    assert _load(".codex-plugin/plugin.json")["mcpServers"] == "./.codex-plugin/mcp.json"
    assert not (REPO_ROOT / ".mcp.json").exists(), "a root .mcp.json is read as project-scope config; see stack-traps"


def test_agent_plugins_mcp_manifest():
    agent_mcp = _load("mcp.json")
    agent_plugin = _load("plugin.json")

    assert agent_mcp["$schema"] == "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
    assert _schema_version(agent_mcp["$schema"]) == _schema_version(agent_plugin["$schema"])
    server = agent_mcp["mcpServers"]["colgrep"]
    assert server["type"] == "stdio"
    for key in server.get("env", {}):
        assert key not in FORBIDDEN_MCP_ENV_KEYS


def test_placeholders_only_in_claude_code_env():
    """Only Claude Code is documented to expand `${…}` in a plugin manifest,
    so only its manifest may carry one, and only in `env`."""
    claude_env = _server(".claude-plugin/mcp.json")["env"]
    assert claude_env == {"COLGREP_MCP_ROOT": "${CLAUDE_PROJECT_DIR}"}
    for relpath in (".codex-plugin/mcp.json", "mcp.json"):
        assert "$" not in json.dumps(_server(relpath).get("env", {})), relpath


def test_names_aligned():
    claude_name = _load(".claude-plugin/plugin.json")["name"]
    agent_name = _load("plugin.json")["name"]
    codex_name = _load(".codex-plugin/plugin.json")["name"]

    assert claude_name == agent_name == codex_name
