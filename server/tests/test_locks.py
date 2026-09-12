from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from colgrep_mcp.locks import project_lock


@pytest.mark.anyio
async def test_same_project_serialises(tmp_path: Path):
    order: list[str] = []

    async def worker(name: str):
        async with project_lock(tmp_path):
            order.append(f"{name}-in")
            await asyncio.sleep(0.01)
            order.append(f"{name}-out")

    await asyncio.gather(worker("a"), worker("b"))
    assert order in (["a-in", "a-out", "b-in", "b-out"], ["b-in", "b-out", "a-in", "a-out"])


@pytest.mark.anyio
async def test_different_projects_overlap(tmp_path: Path):
    (tmp_path / "x").mkdir()
    (tmp_path / "y").mkdir()
    started = asyncio.Event()
    release = asyncio.Event()

    async def hold():
        async with project_lock(tmp_path / "x"):
            started.set()
            await release.wait()

    async def other():
        await started.wait()
        async with project_lock(tmp_path / "y"):
            return "ran"

    t = asyncio.create_task(hold())
    assert await asyncio.wait_for(other(), 1) == "ran"
    release.set()
    await t


def test_lock_key_is_the_path_string(monkeypatch):
    """Two `Path`s with the same string share one lock, and keying never touches the filesystem."""
    from colgrep_mcp.locks import _lock_for

    def _no_resolve(self, *args, **kwargs):  # pragma: no cover - fails the test if reached
        raise AssertionError("_lock_for must not call Path.resolve()")

    monkeypatch.setattr(Path, "resolve", _no_resolve)
    a = _lock_for(Path("/definitely/not/an/existing/project"))
    b = _lock_for(Path("/definitely/not/an/existing/project"))
    assert a is b
    assert _lock_for(Path("/definitely/not/an/existing/other")) is not a
