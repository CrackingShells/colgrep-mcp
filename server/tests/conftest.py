from __future__ import annotations

import os
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def fake_colgrep_bin() -> str:
    p = HERE / "fake_colgrep.py"
    p.chmod(0o755)
    return str(p)


@pytest.fixture
def settings_env(monkeypatch, fake_colgrep_bin, tmp_path) -> dict[str, str]:
    env = {
        "COLGREP_MCP_BINARY": fake_colgrep_bin,
        "COLGREP_MCP_ROOT": str(tmp_path),
        "COLGREP_MCP_TIMEOUT": "30",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return env
