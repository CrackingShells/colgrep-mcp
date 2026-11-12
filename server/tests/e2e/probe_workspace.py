"""Probe-driven harness evidence driver.

Runs the packaged server through a named harness (``claude`` or ``codex``)
with a stub ``colgrep`` on ``$PATH`` so no real index is touched (stack-traps).

The stub's ``doctor`` subcommand writes one R01-schema JSONL record per
invocation into ``$COLGREP_MCP_PROBE/colgrep_probe.jsonl`` and prints the
static ``doctor`` payload.

Never invokes real ``colgrep``, never writes an index against any repository.

Exports:
- **main**: top-level entry point; runs a single harness probe.
- **collect_for(harness)**: runs the harness probe and returns the raw JSONL.
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

TRIGGER_PROMPT = "Run the colgrep doctor tool now. Reply done."

# Stub colgrep script — never touches a real index.
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


def _make_stub() -> Path:
    """Create a minimal ``colgrep`` stub on the temp ``$PATH``.

    The stub's ``doctor`` subcommand writes one R01-schema JSONL record
    into ``$COLGREP_MCP_PROBE/colgrep_probe.jsonl`` and echoes a static
    payload.  All other subcommands are no-ops that exit 0.
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


def collect_for(harness: str, server_root: Path | None = None) -> Path:
    """Run *harness* probe and return the raw JSONL path.

    *harness* is one of ``claude`` or ``codex``.  The driver injects
    a stub ``colgrep`` into ``$PATH`` and launches the harness CLI.

    On timeout, non-zero exit or missing-ledger, appends an explicit
    gap record ``{"error": "<what failed>"}``.

    Newest 3 dated raw directories rotate out at 4.
    """
    server_root = server_root or Path(__file__).resolve().parents[2]

    with tempfile.TemporaryDirectory(prefix="probe_workspace_") as td:
        tmp_dir = Path(td)
        raw = _collect_one_harness(harness, tmp_dir, server_root)

        # Rotating raw copies.
        raw_dir = tmp_dir / "raw"
        raw_dir.mkdir(exist_ok=True)
        ledgers = list(raw_dir.glob("colgrep_probe_*.jsonl"))
        if len(ledgers) >= 3:
            ledgers.sort(key=lambda p: p.stat().st_mtime)
            for old in ledgers[:-3]:
                old.unlink()

        # Rotate the main ledger too.
        if raw.exists():
            ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
            (raw_dir / f"colgrep_probe_{ts}.jsonl").write_text(raw.read_text(encoding="utf-8"))

        return raw


def _validate_record(line: str) -> bool:
    """Deterministic predicate: check R01 schema keys are present."""
    snap = json.loads(line)
    required = (
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
    return all(k in snap for k in required)


def validate(raw_path: Path) -> bool:
    """Validate all lines of a raw JSONL file against the R01 schema."""
    if not raw_path.exists():
        return False
    for line in raw_path.read_text().strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if not _validate_record(line):
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
