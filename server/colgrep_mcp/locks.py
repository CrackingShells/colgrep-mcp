"""The only module owning per-project asyncio locks (R01 §Concurrency invariant).

Callers pass the resolved absolute path `paths.resolve_paths` returns (every
current caller does: `_do_search`, `index_build`, `index_clear`). The lock
key is that path's string, so acquiring a lock costs no filesystem access —
re-resolving here would spend several `lstat` calls per call on a path the
caller already canonicalised.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

_locks: dict[str, asyncio.Lock] = {}


def _lock_for(path: Path) -> asyncio.Lock:
    key = str(path)
    lock = _locks.get(key)
    if lock is None:
        lock = _locks[key] = asyncio.Lock()
    return lock


@asynccontextmanager
async def project_lock(path: Path) -> AsyncIterator[None]:
    """Serialise colgrep invocations that touch the same project."""
    async with _lock_for(path):
        yield
