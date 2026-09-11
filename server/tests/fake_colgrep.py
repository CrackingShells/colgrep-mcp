#!/usr/bin/env python3
"""A stand-in for the colgrep CLI used by the test-suite.

Emulates the subset of colgrep 1.6 surface the adapter drives:
  --version | --stats | settings | status PATH | init [-y] PATH | clear PATH
  [search] [--json] [-k N] [-e PAT] [flags...] QUERY [PATH...]
Environment knobs:
  FAKE_COLGREP_EXIT   force this exit code (stderr gets "forced failure")
  FAKE_COLGREP_HITS   path to a JSON fixture (default: fixtures/hits_small.json)
  FAKE_COLGREP_SLEEP  seconds to sleep before answering (timeout tests)
  FAKE_COLGREP_INDEXED  "0" → `status` reports no index
"""
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = "lightonai/LateOn-Code-edge"


def main(argv):
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
        print(f"  model:       {MODEL} (default)\n  precision:   int8 (build default)\n  k:           25 (default)\n  n:           6 (default)")
        return 0
    if sub == "status":
        path = next((a for a in args[1:] if not a.startswith("-")), ".")
        if os.environ.get("FAKE_COLGREP_INDEXED", "1") == "0":
            print(f"No index found for {path} [{MODEL}]\nRun `colgrep <query>` to create one.")
        else:
            print(f"Project: {path}\nModel:   {MODEL}\nIndex:   /tmp/fake-indices/fake-corpus-deadbeef\n\nRun any search to update the index, or `colgrep clear` to rebuild from scratch.")
        return 0
    if sub == "init":
        for i in range(1, 4):
            sys.stderr.write(f"Indexing {i}/3 files\n")
            sys.stderr.flush()
        print("Indexed 3 code units")
        return 0
    if sub == "clear":
        print("Cleared index")
        return 0

    # search
    fixture = Path(os.environ.get("FAKE_COLGREP_HITS", HERE / "fixtures" / "hits_small.json"))
    hits = json.loads(fixture.read_text())
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
