"""Absolute path stand-ins for the suite's simulated "fake project".

`fake_colgrep.py` never touches these on disk (a hit file that cannot be
read degrades to `""` in `_fill_file_cache`/`_read_file_off_loop`), but real
code checks `pathlib.Path.is_absolute()` against them: the adapter's own
absolute-path guard on `status`/`clear`/`search`, and
`tools_search._resolve_hit_file`'s "already absolute, don't rebase" check.
A bare POSIX-style literal like `/tmp/fake-corpus` is absolute under
`PurePosixPath` but never under `PureWindowsPath` (no drive letter), which
is exactly what breaks once the fake actually runs as a real subprocess on
Windows CI. POSIX keeps today's literal strings unchanged; Windows gets a
drive-rooted equivalent that is genuinely absolute under `PureWindowsPath`
too.

Shared between the pytest test modules (plain import) and `fake_colgrep.py`
(also a plain import: Python puts a directly-run script's own directory —
here, `tests/`, the same directory this module lives in — at `sys.path[0]`).
"""

from __future__ import annotations

import sys

WIN = sys.platform == "win32"

#: The root every "fake project" constant below is rooted under.
FAKE_ROOT = "C:/tmp" if WIN else "/tmp"

FAKE_CORPUS = f"{FAKE_ROOT}/fake-corpus"
FAKE_OTHER = f"{FAKE_ROOT}/other"
FAKE_NEVER_INDEXED = f"{FAKE_ROOT}/never-indexed"
FAKE_PROJ = f"{FAKE_ROOT}/proj"
