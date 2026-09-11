"""Per-project asyncio locks (R01 §Concurrency invariant)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

_locks: dict[str, asyncio.Lock] = {}


def _lock_for(path: Path) -> asyncio.Lock:
    key = str(path.resolve())
    lock = _locks.get(key)
    if lock is None:
        lock = _locks[key] = asyncio.Lock()
    return lock


@asynccontextmanager
async def project_lock(path: Path) -> AsyncIterator[None]:
    """Serialise colgrep invocations that touch the same project."""
    async with _lock_for(path):
        yield
