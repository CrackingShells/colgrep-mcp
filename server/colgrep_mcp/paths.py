"""The only module that resolves a tool's target paths (R01 §Path resolution
invariant, R01 §C2).

Order (the resolution ladder, R01 §Proposed State; sponsor-fold 2026-11-13):
explicit argument → request `_meta` workspace stamp → per-call client roots →
`COLGREP_MCP_ROOT` pin → guarded server cwd (or `ROOT_UNRESOLVED` guidance).

`resolve_target_paths` is the entry point tools call; `resolve_paths` and
`default_root` are the pure pieces underneath it, kept separate so they can
be tested without a request `Context`.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from mcp.server.mcpserver import Context

from .config import Settings
from .errors import Code, tool_error
from .probe import _probe_record  # noqa: F401 - PROBE_ENV is exported via probe.PROBE_ENV
from .server import get_settings

#: Workspace-location keys read from a request `_meta` stamp, in priority
#: order (R03b measured `_meta` vendor keys arriving verbatim on a stamped
#: call).  The leading entries are the documented alias spellings of a host
#: workspace folder; the final entry is the single documented primary key.
#: One list, one idiom (`maintainer-policy`): a resolver reads this list and
#: degrades silently on any absent or non-path value.
META_WORKSPACE_KEYS: tuple[str, ...] = (
    "com.visualstudio.code/workspaceFolder",
    "com.visualstudio.code/workspace",
    "com.example.workspace",
)


def _request_meta(ctx: Context | None) -> dict | None:
    """Best-effort extraction of the request `_meta` mapping (R03b).

    Mirrors `probe.record`'s `getattr` spine so the two agree on what a stamp
    looks like; never raises, never infers.  `meta` is an
    `mcp_types.RequestParamsMeta` — a dict of vendor keys — or `None` when
    the SDK did not surface one.
    """
    try:
        request_ctx = getattr(ctx, "request_context", None) if ctx else None
        meta = getattr(request_ctx, "meta", None) if request_ctx else None
        if meta is None:
            return None
        dumped = meta.model_dump() if hasattr(meta, "model_dump") else meta
        return dict(dumped) if isinstance(dumped, dict) else None
    except Exception:
        return None


def _coerce_workspace_path(raw: str) -> Path | None:
    """Coerce a `_meta` workspace value into an existing absolute directory.

    Accepts a `file:` URI or a plain path; percent- and `~`-decodes it, and
    returns `None` (silently) when it is relative, unparseable, or names no
    existing directory, so a bad stamp degrades to the next ladder rung.
    """
    raw = raw.strip()
    if not raw:
        return None
    try:
        if raw.startswith("file:"):
            raw = url2pathname(urlparse(raw).path)
        # A trailing slash is fine; expand `~` homes before evaluating.
        p = Path(raw).expanduser()
        if not p.is_absolute():
            return None
        p = p.resolve()
        return p if p.is_dir() else None
    except Exception:
        return None


#: Sub-keys unwrapped when a `_meta` workspace value is itself a dict.
_META_PATH_SUBKEYS: tuple[str, ...] = ("workspaceFolder", "root", "uri", "path")


def _meta_to_path(value: object) -> Path | None:
    """Coerce a single `_meta` workspace value into an existing directory or `None`."""
    if isinstance(value, str):
        return _coerce_workspace_path(value)
    if isinstance(value, dict):
        for key in _META_PATH_SUBKEYS:
            sub = value.get(key)
            if isinstance(sub, str):
                path = _coerce_workspace_path(sub)
                if path is not None:
                    return path
    return None


def default_root_from_meta(meta: dict | None) -> Path | None:
    """The workspace directory a request `_meta` stamp names (R03b), or `None`.

    Walks `META_WORKSPACE_KEYS` in priority order and returns the first key
    whose value coerces to an existing directory.  Absent or non-path values
    degrade silently (never raise), falling through to the client-roots rung.
    A dict-valued stamp is unwrapped under a small set of documented
    sub-keys (`workspaceFolder`, `root`, `uri`, `path`) for hosts that nest.
    """
    if not meta:
        return None
    for key in META_WORKSPACE_KEYS:
        value = meta.get(key)
        path = _meta_to_path(value)
        if path is not None:
            return path
    return None


def default_root(settings: Settings, roots: list[Path] | None, meta_root: Path | None = None) -> tuple[Path, str]:
    """Return the default project root and the label of where it came from."""
    if meta_root is not None:
        return meta_root.expanduser().resolve(), "meta"
    if settings.root is not None:
        return settings.root.expanduser().resolve(), "env"
    if roots:
        return roots[0].expanduser().resolve(), "roots"
    return Path.cwd().resolve(), "cwd"


def resolve_paths(
    paths: list[str] | None, settings: Settings, roots: list[Path] | None, meta_root: Path | None = None
) -> list[Path]:
    """Resolve user-supplied paths (or the default root) to existing absolute paths.

    Relative paths are resolved against the default root. Raises ToolError listing
    every path that does not exist, together with the root that was used.
    """
    root, source = default_root(settings, roots, meta_root)
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


#: R03b measured a fresh connection answering the *first* `roots/list` of call
#: 1 with a provisional empty set, then producing the real root a moment later
#: in the same call — and the pre-fix resolver fell to cwd on the first answer,
#: losing the late root.  The fix gives the process's first empty roots answer
#: one bounded reassurance round-trip before concluding "nothing sent", so that
#: late-arriving answer is not beaten by a premature cwd fallback.  Once a call
#: has concluded (empties turn this off on the very first), steady state snaps
#: back to one round-trip per call.  Test harnesses reset this to re-enter the
#: freshly-connected state.
_FIRST_EMPTY_REASSURE = True


async def _client_roots(ctx: Context) -> tuple[list[Path] | None, bool]:
    """`roots`, plus an ``errored`` flag distinguishing a failed round-trip
    from a genuine zero-root answer (R05 M1, probe lever 6).

    ``errored`` is True when the back-channel raised or was absent — the
    probe's ``roots_list`` classifies that as ``error``, not ``empty``.
    """
    global _FIRST_EMPTY_REASSURE
    result = None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = await ctx.session.list_roots()
    except Exception:
        return None, True

    # First empty is provisional (see `_FIRST_EMPTY_REASSURE`): ask once more
    # so a late-arriving root wins over a premature cwd fallback.
    if result is not None and not result.roots and _FIRST_EMPTY_REASSURE:
        _FIRST_EMPTY_REASSURE = False
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result = await ctx.session.list_roots()
        except Exception:
            result = None

    if result is None:
        return None, True
    if not result.roots:
        return None, False
    try:
        # A root is a `file:` URI: `url2pathname` percent-decodes it (a root
        # with a space arrives as `%20`) and, on Windows, turns the URI form
        # `/C:/Users/x` into the drive-rooted path `C:\Users\x` — `Path()` on
        # the raw `.path` did neither, so such roots resolved to nonsense.
        return [Path(url2pathname(root.uri.path)) for root in result.roots if root.uri.path], False
    except Exception:
        return None, True


async def client_roots(ctx: Context) -> list[Path] | None:
    """Best-effort client `roots` (R01 §Path resolution invariant, R05 M1).

    `roots/list` is deprecated as of the 2026-07-28 protocol revision and may
    raise `NoBackChannelError` (or just a deprecation warning) on a client
    with no back-channel; either way this degrades to `None` rather than
    fail the tool call, leaving `resolve_paths` to fall through to cwd.
    """
    roots, _errored = await _client_roots(ctx)
    return roots


def _roots_can_matter(paths: list[str] | None, settings: Settings, meta_root: Path | None = None) -> bool:
    """Whether `client_roots` could change what `resolve_paths` returns.

    The client root is consulted only when no earlier rung has already
    settled the default root *and* something still has to be resolved against
    a default root: no paths at all, or at least one relative path.  Under
    the Claude Code plugin the env root is always set, so every `search` used
    to pay a `roots/list` round-trip whose answer could not be used.  A
    request `_meta` stamp outranks roots, so it suppresses the round-trip too.
    """
    if meta_root is not None:
        return False
    if settings.root is not None:
        return False
    if not paths:
        return True
    return any(not Path(raw).expanduser().is_absolute() for raw in paths)


async def resolve_target_paths(ctx: Context, paths: list[str] | None) -> list[Path]:
    """`resolve_paths` for a tool call, resolving the per-call default root.

    Reads a request `_meta` workspace stamp (rung 2a) before consulting the
    per-call client roots (rung 2b, only when the earlier rungs left the
    default root unsettled).
    """
    settings = get_settings(ctx)
    meta_root = default_root_from_meta(_request_meta(ctx))
    if _roots_can_matter(paths, settings, meta_root):
        roots, roots_error = await _client_roots(ctx)
    else:
        roots, roots_error = None, False

    # Probe hook: best-effort dump of the resolution outcome (maintainer-policy
    # section *One idiom per concern*: use ``safe_log`` on failure).  Always
    # inert when COLGREP_MCP_PROBE is unset; never alters the resolved result.
    _probe_record(ctx, paths, settings, roots, roots_error=roots_error)

    return resolve_paths(paths, settings, roots, meta_root)
