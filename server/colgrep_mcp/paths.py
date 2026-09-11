"""Path resolution shared by every path-taking tool (R01 §Path resolution invariant).

Order: explicit argument → COLGREP_MCP_ROOT → first client root → server cwd.
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.mcpserver.exceptions import ToolError

from .config import Settings


def default_root(settings: Settings, roots: list[Path] | None) -> tuple[Path, str]:
    """Return the default project root and the label of where it came from."""
    if settings.root is not None:
        return settings.root.expanduser().resolve(), "env"
    if roots:
        return roots[0].expanduser().resolve(), "roots"
    return Path.cwd().resolve(), "cwd"


def resolve_paths(paths: list[str] | None, settings: Settings, roots: list[Path] | None) -> list[Path]:
    """Resolve user-supplied paths (or the default root) to existing absolute paths.

    Relative paths are resolved against the default root. Raises ToolError listing
    every path that does not exist, together with the root that was used.
    """
    root, source = default_root(settings, roots)
    if not paths:
        if not root.exists():
            raise ToolError(f"Default root {root} (from {source}) does not exist. Pass `paths` explicitly.")
        return [root]
    resolved: list[Path] = []
    missing: list[str] = []
    for raw in paths:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = root / p
        p = p.resolve()
        if p.exists():
            resolved.append(p)
        else:
            missing.append(raw)
    if missing:
        raise ToolError(
            f"Path(s) not found: {', '.join(missing)} (relative paths are resolved against {root}, from {source})."
        )
    return resolved
