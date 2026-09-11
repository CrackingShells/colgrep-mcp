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
    (tmp_path / "x").mkdir(); (tmp_path / "y").mkdir()
    started = asyncio.Event(); release = asyncio.Event()

    async def hold():
        async with project_lock(tmp_path / "x"):
            started.set(); await release.wait()

    async def other():
        await started.wait()
        async with project_lock(tmp_path / "y"):
            return "ran"

    t = asyncio.create_task(hold())
    assert await asyncio.wait_for(other(), 1) == "ran"
    release.set(); await t
