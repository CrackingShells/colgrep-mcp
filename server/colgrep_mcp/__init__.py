"""colgrep-mcp: an MCP server that exposes colgrep semantic code search to agents."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("colgrep-mcp")
except PackageNotFoundError:
    # Only reachable when the source tree is imported without the project
    # ever having been installed (editable or otherwise) into the active
    # environment -- never true under `uv run`, which installs the project
    # editable before running anything.
    __version__ = "0.0.0+unknown"
