"""Inert, dump-only probe that records workspace-signal snapshots (R01).

With ``COLGREP_MCP_PROBE`` unset, no file is touched, no tool surface changes,
no resolution path changes.  When set, ``record(...)`` appends a single JSONL
line to ``$COLGREP_MCP_PROBE/colgrep_probe.jsonl``.

The probe must never raise into the resolve chain (maintainer-policy
section *One idiom per concern*: use ``safe_log`` on failure).

Report references: R01 section Probe dump schema.
"""

from __future__ import annotations

import inspect
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROBE_ENV = "COLGREP_MCP_PROBE"
_LOG = logging.getLogger("colgrep_mcp")


def capture_pure(snap: dict[str, Any]) -> str:
    """Serialise *snap* to one JSONL line with sorted, deterministic keys."""
    return json.dumps(snap, sort_keys=True, ensure_ascii=False)


def _try_dump(obj: Any) -> Any:
    """``obj.model_dump()`` when available, else *obj* as-is."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj


def _probe_tool_name() -> str:
    """Best-effort tool name from the call stack.

    Walks frames up starting from the first caller of ``record`` to find the
    first non-colgrep_mcp function — usually a tool handler like ``search``,
    ``expand``, ``doctor``, etc.
    """
    try:
        frame = inspect.currentframe()
        depth = 0
        while frame:
            name = frame.f_code.co_name
            if depth > 0 and name != "_probe_record" and not name.startswith("_probe"):
                return name
            frame = frame.f_back
            depth += 1
    except Exception:
        pass
    return "probe"


def record(
    ctx: Any,
    raw_paths: list[str] | None,
    settings_root: Path | None,
    roots: list[Path] | None,
    resolved_root: Path,
    resolved_source: str,
) -> None:
    """Append one JSONL probe record to the ledger file.

    *ctx* is the MCP ``Context`` (or ``None`` in tests).  ``init_capabilities``
    and ``request_meta`` are pulled via ``getattr`` from
    ``ctx.request_context`` — SDK absent or fragment yields ``None``, never
    inferred (R01 section Contracts & Invariants).

    *settings_root* and *roots* are the values produced by ``get_settings`` and
    ``client_roots`` respectively at the call site — the probe records the
    actual outcome, not a second pass (maintainer-policy section *hardware first*).

    Best-effort I/O with ``safe_log`` on failure; never raises.
    """
    probe_dir = os.environ.get(PROBE_ENV)
    if not probe_dir:
        return

    from . import logging_utils

    # Build roots_list from the *shared* client_roots call — no double round-trip.
    if settings_root is not None:
        roots_static = "declared"  # COLGREP_MCP_ROOT pin present.
    elif roots is not None:
        roots_static = "declared"  # client_roots actually returned items.
    else:
        roots_static = "empty"  # no pin, no client roots.

    roots_list_data: dict[str, Any] = {
        "static": roots_static,
        "items": [str(r) for r in roots] if roots else [],
    }

    # Extract SDK fields via getattr (may not exist in every SDK version).
    init_caps = None
    req_meta = None
    try:
        request_ctx = getattr(ctx, "request_context", None) if ctx else None
        init_caps = _try_dump(getattr(request_ctx, "initialize", None)) if request_ctx else None
        req_meta = _try_dump(getattr(request_ctx, "meta", None)) if request_ctx else None
    except Exception:
        init_caps = None
        req_meta = None

    env_snapshot: dict[str, str | None] = {
        "COLGREP_MCP_ROOT": os.environ.get("COLGREP_MCP_ROOT"),
        "COLGREP_MCP_BINARY": os.environ.get("COLGREP_MCP_BINARY"),
        "spawn_env_digest": os.environ.get("COLGREP_MCP_SPAWN_ENV_DIGEST"),
    }

    record_obj = {
        "ts": datetime.now(UTC).isoformat(),
        "server_pid": os.getpid(),
        "tool": _probe_tool_name(),
        "raw_paths": raw_paths,
        "env": env_snapshot,
        "init_capabilities": init_caps,
        "request_meta": req_meta,
        "roots_list": roots_list_data,
        "resolved": {"root": str(resolved_root), "source": resolved_source},
        "cwd": str(Path.cwd()),
    }

    line = capture_pure(record_obj)
    try:
        log_path = Path(probe_dir) / "colgrep_probe.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        try:
            session = getattr(getattr(ctx, "request_context", None), "session", None)
            logging_utils.safe_log(session, "debug", f"probe write failed: {line}")
        except Exception:
            _LOG.debug("probe write failed: %s", line)


def _probe_record(ctx: Any, paths: list[str] | None, settings: Any, roots: list[Path] | None) -> None:
    """Called from ``paths.resolve_target_paths`` after ``client_roots``.

    Reuses ``default_root`` (the pure function) to build the resolved output
    — no second resolution pass, just a label walk.
    """
    from .paths import default_root

    settings_root = settings.root if hasattr(settings, "root") else getattr(settings, "root", None)
    resolved_root, resolved_source = default_root(settings, roots)
    record(ctx, paths, settings_root, roots, resolved_root, resolved_source)
