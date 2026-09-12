#!/usr/bin/env python3
"""A stand-in for the colgrep CLI used by the test-suite.

Emulates the subset of colgrep 1.6 surface the adapter drives:
  --version | --stats | settings | status PATH | init [-y] PATH | clear PATH
  [search] [--json] [-k N] [-e PAT] [flags...] QUERY [PATH...]
Environment knobs:
  FAKE_COLGREP_EXIT       force this exit code (stderr gets "forced failure")
  FAKE_COLGREP_HITS       path to a JSON fixture (default: fixtures/hits_small.json)
  FAKE_COLGREP_SLEEP      seconds to sleep before answering (timeout tests)
  FAKE_COLGREP_INDEXED    "0" -> `status` reports no index
  FAKE_COLGREP_ARGV_FILE  path to write argv (as a JSON list) to, for adapter tests
                          that need to assert exactly what was executed
  FAKE_COLGREP_UPTODATE   "1" -> `init` emits the "Index is up to date" stderr
                          line (R05 D2) instead of the cold-build summary
  FAKE_COLGREP_RAW_STDOUT path to a file printed verbatim to stdout (exit 0)
                          for a search call, bypassing FAKE_COLGREP_HITS
                          entirely — used to simulate malformed/non-JSON
                          output for ColgrepParseError tests
  FAKE_COLGREP_STATUS_PROJECT  when set, `status` reports this as the
                          `Project:` line instead of echoing the requested
                          path — simulates colgrep folding a path into an
                          already-registered ancestor project (R05 D3)
"""
import json
import os
import sys
import time
from pathlib import Path

from fixture_paths import FAKE_CORPUS

HERE = Path(__file__).resolve().parent
MODEL = "lightonai/LateOn-Code-edge"


def main(argv):
    # Force UTF-8 with bare `\n` line endings regardless of platform. Python's
    # default text-mode stdout/stderr on Windows (a) encodes with the
    # console/legacy codepage, which cannot represent the emoji this script
    # prints (`clear`/`init`) and crashes with `UnicodeEncodeError`, and (b)
    # translates every `\n` this script writes into `\r\n`, which the
    # adapter's stats-block regex (`_STATS_BLOCK_RE`, an exact `\d+\n` match)
    # cannot parse. The real colgrep binary is a native executable that never
    # does either translation, on any OS, so this just makes the stand-in
    # match the real thing instead of leaking a Python/Windows console quirk
    # into the adapter's contract. POSIX stdio is already UTF-8/`\n`, so this
    # is a no-op there.
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    sys.stderr.reconfigure(encoding="utf-8", newline="\n")

    if os.environ.get("FAKE_COLGREP_ARGV_FILE"):
        Path(os.environ["FAKE_COLGREP_ARGV_FILE"]).write_text(json.dumps(argv))

    if os.environ.get("FAKE_COLGREP_SLEEP"):
        time.sleep(float(os.environ["FAKE_COLGREP_SLEEP"]))
    forced = os.environ.get("FAKE_COLGREP_EXIT")
    if forced and forced != "0":
        sys.stderr.write("error: forced failure\n")
        return int(forced)

    args = [a for a in argv if a != "--color" and a != "never"]
    if "--version" in args:
        print("colgrep 1.6.2")
        return 0
    if "--stats" in args:
        print(f"Project: /tmp/fake-corpus\n  Model: {MODEL}\n  Functions indexed: 3\n  Search count: 7\n")
        print(f"Project: /tmp/other\n  Model: {MODEL}\n  Functions indexed: 649\n  Search count: 1\n")
        return 0
    sub = args[0] if args else ""
    if sub == "settings":
        print("Current configuration:\n")
        print(
            f"  model:       {MODEL} (default)\n  precision:   int8 (build default)\n"
            "  k:           25 (default)\n  n:           6 (default)"
        )
        return 0
    if sub == "status":
        path = next((a for a in args[1:] if not a.startswith("-")), ".")
        if os.environ.get("FAKE_COLGREP_INDEXED", "1") == "0":
            print(f"No index found for {path} [{MODEL}]\nRun `colgrep <query>` to create one.")
        else:
            project = os.environ.get("FAKE_COLGREP_STATUS_PROJECT", path)
            print(
                f"Project: {project}\nModel:   {MODEL}\n"
                "Index:   /tmp/fake-indices/fake-corpus-deadbeef\n\n"
                "Run any search to update the index, or `colgrep clear` to rebuild from scratch."
            )
        return 0
    if sub == "init":
        path = next((a for a in args[1:] if not a.startswith("-")), ".")
        if os.environ.get("FAKE_COLGREP_UPTODATE") == "1":
            sys.stderr.write(f"Index is up to date for {path} (156 files)\n")
        else:
            # Realistic cold-init stderr shape (R05 D2 / evidence/colgrep/01_cold_init.stderr.txt):
            # a two-line model/build banner, then one summary line — no per-file progress.
            sys.stderr.write(f"\U0001f916 Model: {MODEL} (CPU)\n")
            sys.stderr.write("\U0001f4c2 Building index...\n")
            sys.stderr.flush()
            sys.stderr.write(f"Indexed {path} (added: 155, changed: 1, deleted: 199, unchanged: 0)\n")
        return 0
    if sub == "clear":
        path = next((a for a in args[1:] if not a.startswith("-")), ".")
        print(f"\U0001f5d1️  Cleared index for {path} [{MODEL}]")
        return 0

    # search
    if os.environ.get("FAKE_COLGREP_RAW_STDOUT"):
        sys.stdout.write(Path(os.environ["FAKE_COLGREP_RAW_STDOUT"]).read_text())
        return 0

    fixture = Path(os.environ.get("FAKE_COLGREP_HITS", HERE / "fixtures" / "hits_small.json"))
    # Fixture JSON hard-codes hit files under the POSIX-style "/tmp/fake-corpus"
    # stand-in project; on POSIX that is already absolute, so
    # `_resolve_hit_file` leaves it untouched, but the same literal is never
    # absolute under `PureWindowsPath` (no drive letter), so it gets silently
    # rebased under the search root instead. Swap in `FAKE_CORPUS`, which is
    # the same literal on POSIX (no-op replace) and a drive-rooted equivalent
    # on Windows (genuinely absolute there too).
    hits = json.loads(fixture.read_text().replace("/tmp/fake-corpus", FAKE_CORPUS))
    if "-k" in args:
        k = int(args[args.index("-k") + 1])
        hits = hits[:k]
    if "--json" in args:
        print(json.dumps(hits, indent=2))
    else:
        for h in hits:
            u = h["unit"]
            print(f"{u['file']}:{u['line']}-{u['end_line']}  {u['signature']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
