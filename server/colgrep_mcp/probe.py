"""Inert, dump-only probe that records workspace-signal snapshots (R01).

With ``COLGREP_MCP_PROBE`` unset, no file is touched, no tool surface changes,
no resolution path changes.  When set, ``record(...)`` appends a single JSONL
line to ``$COLGREP_MCP_PROBE/colgrep_probe.jsonl``.

The probe must never raise into the resolve chain (maintainer-policy
section *One idiom per concern*: use ``safe_log`` on failure).  ``record`` is
total: no input — ``ctx=None``, a non-serializable snapshot value, an
unwritable probe dir — may raise past the resolve call site.  Every ledger
column reflects what was measured, never what the probe can guess: the
``tool`` column is attributed from the actual calling tool (never ``"record"``)
and ``roots_list.static`` distinguishes ``declared`` / ``empty`` / ``error``.

Report references: R01 section Probe dump schema;
02-gap_analysis_calibrated_probe_v0.md (four defect lines each step repairs);
02-findings_probe_verifier_v0.md (lever table).
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

# Canonical stub-authored record (lever 1b): the exact fabricated line the stub
# driver used to write, whose `init_capabilities`/`roots_list` values a running
# harness never sent.  The calibration oracle (forge_record/diff_record) must
# whistle on this verbatim fabrication.
FORGED_SAMPLE: dict[str, Any] = {
    "ts": "2026-01-01T00:00:00+00:00",
    "server_pid": 1,
    "tool": "doctor",
    "raw_paths": None,
    "env": {
        "COLGREP_MCP_ROOT": None,
        "COLGREP_MCP_BINARY": None,
        "spawn_env_digest": None,
    },
    "init_capabilities": {"protocolVersion": "NONE"},
    "request_meta": None,
    "roots_list": {"static": "empty", "items": []},
    "resolved": {"root": "", "source": "cwd"},
    "cwd": "/stub/cwd",
    "provenance": "stub",
}

_LOG = logging.getLogger("colgrep_mcp")

# Functions that live inside the probe/resolve machinery and must never be
# mistaken for the tool handler that surfaced a record (lever 1: the frame
# scan used to resolve to ``record`` itself every time).
_PROBE_INTERNAL_NAMES = frozenset(
    {
        "record",
        "_probe_record",
        "_probe_tool_name",
        "capture_pure",
        "forge_record",
        "diff_record",
        "resolve_target_paths",
        "resolve_paths",
        "default_root",
        "_roots_can_matter",
        "client_roots",
        "_client_roots",
    }
)


def capture_pure(snap: dict[str, Any]) -> str:
    """Serialise *snap* to one JSONL line with sorted, deterministic keys.

    ``default=str`` coerces a value with no native JSON encoding so the record
    stays a witness (lever 2b: an unmappable snapshot value must not turn into
    a ``TypeError`` that escapes the never-raise boundary).
    """
    return json.dumps(snap, sort_keys=True, ensure_ascii=False, default=str)


def _try_dump(obj: Any) -> Any:
    """``obj.model_dump()`` when available, else *obj* as-is."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj


def _probe_tool_name() -> str:
    """Best-effort tool name from the call stack (lever 1 repair).

    Walks frames upward from the first caller of ``record``, skipping module
    internal names (including ``record`` itself), to find the first function
    that stands for a real tool handler — ``search``, ``expand``, ``doctor``,
    ``find_files``, etc.  Falls back to ``"probe"``.
    """
    try:
        frame = inspect.currentframe()
        frame = frame.f_back if frame is not None else None
        while frame is not None:
            name = frame.f_code.co_name
            if name not in _PROBE_INTERNAL_NAMES:
                return name
            frame = frame.f_back
    except Exception:
        pass
    return "probe"


def _classify_roots(settings_root: Path | None, roots: list[Path] | None, roots_error: bool) -> str:
    """Truth-source ``roots_list.static`` (lever 6 / gap defect 6).

    - ``declared``: a ``COLGREP_MCP_ROOT`` pin is present, or ``client_roots``
      actually returned items.
    - ``error``: the ``roots/list`` round-trip raised or the back-channel was
      absent — we could not ask, which is not the same as nothing sent.
    - ``empty``: only when a client genuinely answered with zero roots.
    """
    if settings_root is not None:
        return "declared"
    if roots is not None:
        return "declared"
    if roots_error:
        return "error"
    return "empty"


def record(
    ctx: Any,
    raw_paths: list[str] | None,
    settings_root: Path | None,
    roots: list[Path] | None,
    resolved_root: Path,
    resolved_source: str,
    *,
    roots_error: bool = False,
    tool: str | None = None,
) -> None:
    """Append one JSONL probe record to the ledger file.

    *ctx* is the MCP ``Context`` (or ``None`` in tests).  ``init_capabilities``
    and ``request_meta`` are pulled via ``getattr`` from
    ``ctx.request_context`` — SDK absent or fragment yields ``None``, never
    inferred (R01 section Contracts & Invariants).

    *tool* names the actual calling tool when known (the hook site passes it);
    otherwise it is resolved from the stack, never assumed to be ``"record"``.
    *roots_error* tells the ``roots_list`` classification that the round-trip
    failed rather than that the client sent nothing.

    Best-effort and total: every failure path is swallowed via ``safe_log``/
    a log line and never surfaces past this call (lever 2b).
    """
    probe_dir = os.environ.get(PROBE_ENV)
    if not probe_dir:
        return

    try:
        # Build roots_list from the classification, not a second round-trip.
        roots_list_data: dict[str, Any] = {
            "static": _classify_roots(settings_root, roots, roots_error),
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
            "tool": tool if tool is not None else _probe_tool_name(),
            "raw_paths": raw_paths,
            "env": env_snapshot,
            "init_capabilities": init_caps,
            "request_meta": req_meta,
            "roots_list": roots_list_data,
            "resolved": {"root": str(resolved_root), "source": resolved_source},
            "cwd": str(Path.cwd()),
        }

        line = capture_pure(record_obj)
        log_path = Path(probe_dir) / "colgrep_probe.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        # Total boundary: an unmappable snapshot value, a serialization
        # failure, or an unwritable probe dir must never break the caller.
        try:
            _LOG.debug("probe write failed; continuing without a record")
        except Exception:
            pass


def _probe_record(
    ctx: Any,
    paths: list[str] | None,
    settings: Any,
    roots: list[Path] | None,
    *,
    roots_error: bool = False,
    tool: str | None = None,
) -> None:
    """Called from ``paths.resolve_target_paths`` after ``client_roots``.

    Reuses ``default_root`` (the pure function) to build the resolved output
    — no second resolution pass, just a label walk.
    """
    from .paths import default_root

    settings_root = settings.root if hasattr(settings, "root") else getattr(settings, "root", None)
    resolved_root, resolved_source = default_root(settings, roots)
    record(
        ctx,
        paths,
        settings_root,
        roots,
        resolved_root,
        resolved_source,
        roots_error=roots_error,
        tool=tool,
    )


def forge_record(**overrides: Any) -> dict[str, Any]:
    """Build a ground-truth record from an explicit snapshot (calibration).

    No frame reading, no ``os.environ`` reading — every field is either the
    static default or an explicit ``**overrides`` value, so a harness can
    construct the record a *truthful* probe *should* have written and differ
    it against the ledger to catch a probe that lies.
    """
    record_obj: dict[str, Any] = {
        "ts": "2026-01-01T00:00:00+00:00",
        "server_pid": 1,
        "tool": "search",
        "raw_paths": None,
        "env": {
            "COLGREP_MCP_ROOT": None,
            "COLGREP_MCP_BINARY": None,
            "spawn_env_digest": None,
        },
        "init_capabilities": None,
        "request_meta": None,
        "roots_list": {"static": "empty", "items": []},
        "resolved": {"root": "/truth/root", "source": "cwd"},
        "cwd": "/truth/cwd",
    }
    record_obj.update(overrides)
    return record_obj


def diff_record(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    """Field-level disagreements between *expected* truth and *actual*.

    Returns a list of disagreement strings, one per field whose value
    differs; empty when the two records agree on every key.
    """
    disagreements: list[str] = []
    for key in sorted(set(expected) | set(actual)):
        if expected.get(key) != actual.get(key):
            disagreements.append(f"{key}: expected {expected.get(key)!r}, got {actual.get(key)!r}")
    return disagreements
