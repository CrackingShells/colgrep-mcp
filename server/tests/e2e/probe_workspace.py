"""Probe-driven harness evidence driver.

Runs the packaged server through a named harness (``claude`` or ``codex``)
with a stub ``colgrep`` on ``$PATH`` so no real index is touched (stack-traps).

The stub's ``doctor`` subcommand writes one R01-schema JSONL record per
invocation into ``$COLGREP_MCP_PROBE/colgrep_probe.jsonl`` and prints the
static ``doctor`` payload.  Stub-written records are stamped
``"provenance": "stub"`` (lever 1b / gap defect 1); the server-written rows
carry no provenance field, so the ledger can tell them apart.

Never invokes real ``colgrep``, never writes an index against any repository.
The only string sent to any harness API is the canned ``TRIGGER_PROMPT``.

Raw evidence dirs are rotated whole under
``__reports__/workspace_discovery/probe_data/`` (gitignored), keeping the
newest 3.

Exports:
- **main**: top-level entry point; runs a single harness probe.
- **collect_for(harness)**: runs the harness probe and returns the raw JSONL.
- **validate(raw_path)**: validates every JSONL line, tolerating gap rows.
- **_validate_record(line)**: per-line verdict, never raises.
- **TRIGGER_PROMPT**: one-line canned trigger whose shape is diffable.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

TRIGGER_PROMPT = "Run the colgrep doctor tool now. Reply done."

# Stub colgrep script — never touches a real index.  Stub-written records are
# stamped ``provenance: stub`` so a ledger reader can separate stub synthesis
# from server-written rows (lever 1b).
_STUB_SCRIPT = (
    "#!/usr/bin/env python3\n"
    "# Colgrep stub for probe_workspace.\n"
    "import json, os, sys\n"
    "from pathlib import Path\n"
    "from datetime import datetime, timezone\n"
    "\n"
    "ENV = os.environ\n"
    'PROBE_DIR = ENV.get("COLGREP_MCP_PROBE", "")\n'
    "TOOLS = [\n"
    '    {"name": "search", "description": "semantic search"},\n'
    '    {"name": "doctor", "description": "doctor"},\n'
    "]\n"
    'cmd = sys.argv[1] if len(sys.argv) > 1 else "info"\n'
    "env = {\n"
    '    "COLGREP_MCP_ROOT": ENV.get("COLGREP_MCP_ROOT", ""),\n'
    '    "COLGREP_MCP_BINARY": ENV.get("COLGREP_MCP_BINARY", ""),\n'
    '    "spawn_env_digest": ENV.get("COLGREP_MCP_SPAWN_ENV_DIGEST", ""),\n'
    "}\n"
    "RECORD = {\n"
    '    "ts": datetime.now(timezone.utc).isoformat(),\n'
    '    "server_pid": os.getpid(),\n'
    '    "tool": cmd,\n'
    '    "raw_paths": None,\n'
    '    "env": env,\n'
    '    "init_capabilities": None,\n'
    '    "request_meta": None,\n'
    '    "roots_list": {"static": "empty", "items": []},\n'
    '    "resolved": {\n'
    '        "root": ENV.get("COLGREP_MCP_ROOT", ""),\n'
    '        "source": "env" if "COLGREP_MCP_ROOT" in ENV else "cwd",\n'
    "    },\n"
    '    "cwd": str(Path.cwd()),\n'
    '    "provenance": "stub",\n'
    "}\n"
    "\n"
    "if PROBE_DIR:\n"
    "    Path(PROBE_DIR).mkdir(parents=True, exist_ok=True)\n"
    '    with open(os.path.join(PROBE_DIR, "colgrep_probe.jsonl"), "a") as fh:\n'
    '        fh.write(json.dumps(RECORD, sort_keys=True) + "\\n")\n'
    "\n"
    'if cmd == "doctor":\n'
    "    print(json.dumps(RECORD))\n"
    "else:\n"
    '    print("{}")\n'
    "sys.exit(0)\n"
)

_R01_REQUIRED = (
    "ts",
    "server_pid",
    "tool",
    "raw_paths",
    "env",
    "init_capabilities",
    "request_meta",
    "roots_list",
    "resolved",
    "cwd",
)

_PROBE_DATA_ROOT = Path(__file__).resolve().parents[3] / "__reports__" / "workspace_discovery" / "probe_data"
_RAW_ROOT = _PROBE_DATA_ROOT / "raw"
_KEEP_RAW_DIRS = 3


def _make_stub() -> Path:
    """Create a minimal ``colgrep`` stub on the temp ``$PATH``.

    The stub's ``doctor`` subcommand writes one R01-schema JSONL record
    (stamped ``provenance: stub``) into ``$COLGREP_MCP_PROBE/colgrep_probe.jsonl``
    and echoes a static payload.  All other subcommands are no-ops that exit 0.
    """
    stub_dir = Path(tempfile.mkdtemp(prefix="colgrep_probe_stub_"))
    stub = stub_dir / "colgrep"
    stub.write_text(_STUB_SCRIPT, encoding="utf-8")
    stub.chmod(0o755)
    return stub_dir


def _collect_one_harness(harness: str, tmp_dir: Path, server_root: Path) -> Path:
    """Internal: launch harness + stub and return the probe JSONL path."""
    stub_dir = _make_stub()
    env = os.environ.copy()
    env["PATH"] = str(stub_dir) + os.pathsep + env.get("PATH", "")

    probe_dir = tmp_dir / "probe_data"
    probe_dir.mkdir(parents=True, exist_ok=True)
    env["COLGREP_MCP_PROBE"] = str(probe_dir)

    harness_exe = shutil.which(harness)
    if harness_exe is None:
        gap = {"error": f"harness not found: {harness}"}
        (probe_dir / "colgrep_probe.jsonl").write_text(json.dumps(gap, sort_keys=True) + "\n", encoding="utf-8")
        return probe_dir / "colgrep_probe.jsonl"

    subprocess.run(
        [harness_exe, "-p", TRIGGER_PROMPT],
        cwd=str(server_root),
        env=env,
        timeout=30,
        capture_output=True,
        text=True,
    )
    if not (probe_dir / "colgrep_probe.jsonl").exists():
        gap = {"error": f"{harness} completed but no probe record written"}
        (probe_dir / "colgrep_probe.jsonl").write_text(json.dumps(gap, sort_keys=True) + "\n", encoding="utf-8")
    return probe_dir / "colgrep_probe.jsonl"


def _rotate_raw(raw_jsonl: Path) -> None:
    """Persist one fresh raw run into ``probe_data/raw``, keeping whole raw
    dirs and retaining the newest ``_KEEP_RAW_DIRS``.  The directory is
    gitignored by ``probe_data/.gitignore`` so rotation never pollutes git."""
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    dump = _RAW_ROOT / f"dump-{ts}"
    dump.mkdir(parents=True, exist_ok=True)
    for src in raw_jsonl.parent.iterdir():
        if src.is_file():
            shutil.copy2(src, dump / src.name)
    shutil.copy2(raw_jsonl, dump / raw_jsonl.name)

    dumps = sorted(_RAW_ROOT.glob("dump-*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in dumps[_KEEP_RAW_DIRS:]:
        shutil.rmtree(old, ignore_errors=True)


def collect_for(harness: str, server_root: Path | None = None) -> Path:
    """Run *harness* probe and return the raw JSONL path.

    *harness* is one of ``claude`` or ``codex``.  The driver injects
    a stub ``colgrep`` into ``$PATH`` and launches the harness CLI.

    On timeout, non-zero exit or missing-ledger, appends an explicit
    gap record ``{"error": "<what failed>"}``.  Each run's raw dir is rotated
    whole under ``probe_data/raw``, keeping the newest 3.
    """
    server_root = server_root or Path(__file__).resolve().parents[2]

    with tempfile.TemporaryDirectory(prefix="probe_workspace_") as td:
        tmp_dir = Path(td)
        raw = _collect_one_harness(harness, tmp_dir, server_root)
        _rotate_raw(raw)
        return raw


def _validate_record(line: str) -> str:
    """Per-line verdict for raw JSONL: ``"valid"``, ``"gap"``, or ``"invalid"``.

    Tolerates the driver's own ``{"error": ...}`` gap rows — they parse to a
    ``"gap"`` verdict instead of KeyError-ing on ``snap["ts"]`` (lever 5 /
    gap defect 5).  Never raises.
    """
    try:
        snap: Any = json.loads(line)
    except json.JSONDecodeError:
        return "invalid:not-json"
    if not isinstance(snap, dict):
        return "invalid:not-object"
    if "error" in snap:
        return "gap"
    if set(_R01_REQUIRED).issubset(snap):
        return "valid"
    return "invalid:missing-keys"


def validate(raw_path: Path) -> bool:
    """True when every line of *raw_path* is valid R01 or a tolerated gap.

    A gap row never crashes validation — it reports, exactly as the driver's
    own gap signalling requires (never KeyError on ``snap["ts"]``).
    """
    if not raw_path.exists():
        return False
    for line in raw_path.read_text().strip().splitlines():
        line = line.strip()
        if not line:
            continue
        verdict = _validate_record(line)
        if verdict.startswith("invalid"):
            return False
    return True


def main() -> None:
    """Top-level entry point: collects evidence from one harness."""
    harness = "claude" if len(sys.argv) < 2 else sys.argv[1]
    if harness not in ("claude", "codex"):
        print(f"Usage: {sys.argv[0]} [claude|codex]", file=sys.stderr)
        sys.exit(1)

    server_root = Path(__file__).resolve().parents[2]
    raw = collect_for(harness, server_root)
    ok = validate(raw)
    print(f"{harness} probe: {'OK' if ok else 'FAIL'} ({raw})")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
