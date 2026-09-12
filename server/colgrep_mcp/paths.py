"""The only module that resolves a tool's target paths (R01 §Path resolution
invariant, R01 §C2).

Order: explicit argument → COLGREP_MCP_ROOT → first client root → server cwd.

`resolve_target_paths` is the entry point tools call; `resolve_paths` and
`default_root` are the pure pieces underneath it, kept separate so they can
be tested without a request `Context`.
"""

from __future__ import annotations

import warnings
from pathlib import Path

from mcp.server.mcpserver import Context

from .config import Settings
from .errors import Code, tool_error
from .server import get_settings


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
            raise tool_error(Code.PATH_NOT_FOUND, f"Default root {root} (from {source}) does not exist.")
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
        raise tool_error(
            Code.PATH_NOT_FOUND,
            f"Path(s) not found: {', '.join(missing)} (relative paths are resolved against {root}, from {source}).",
        )
    return resolved


async def client_roots(ctx: Context) -> list[Path] | None:
    """Best-effort client `roots` (R01 §Path resolution invariant, R05 M1).

    `roots/list` is deprecated as of the 2026-07-28 protocol revision and may
    raise `NoBackChannelError` (or just a deprecation warning) on a client
    with no back-channel; either way this degrades to `None` rather than
    fail the tool call, leaving `resolve_paths` to fall through to cwd.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = await ctx.session.list_roots()
    except Exception:
        return None
    if not result.roots:
        return None
    try:
        return [Path(root.uri.path) for root in result.roots if root.uri.path]
    except Exception:
        return None


def _roots_can_matter(paths: list[str] | None, settings: Settings) -> bool:
    """Whether `client_roots` could change what `resolve_paths` returns.

    The client root is consulted only when no `COLGREP_MCP_ROOT` is set *and*
    something still has to be resolved against a default root: no paths at
    all, or at least one relative path. Under the Claude Code plugin the env
    root is always set, so every `search` used to pay a `roots/list`
    round-trip whose answer could not be used.
    """
    if settings.root is not None:
        return False
    if not paths:
        return True
    return any(not Path(raw).expanduser().is_absolute() for raw in paths)


async def resolve_target_paths(ctx: Context, paths: list[str] | None) -> list[Path]:
    """`resolve_paths` for a tool call, fetching client roots only when they can matter."""
    settings = get_settings(ctx)
    roots = await client_roots(ctx) if _roots_can_matter(paths, settings) else None
    return resolve_paths(paths, settings, roots)
