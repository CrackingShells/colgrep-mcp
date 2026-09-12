from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "real_colgrep: exercises the real colgrep binary (read-only calls only); skipped unless COLGREP_MCP_REAL=1.",
    )


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def fake_colgrep_bin(tmp_path) -> str:
    """Path to something the adapter can `create_subprocess_exec` as `colgrep`.

    `fake_colgrep.py` is a Python script, not a native executable. POSIX is
    fine with that (the shebang plus the executable bit makes it directly
    runnable); Windows' `CreateProcess` cannot launch a `.py` file at all —
    it fails with `OSError: [WinError 193] %1 is not a valid Win32
    application` before the fake ever runs, which is the fixture-level bug
    behind the whole Windows CI failure (every downstream symptom — tool
    errors, missing `argv.json`, `DID NOT RAISE TimeoutError` — follows from
    that one exec never succeeding).

    On Windows we point `COLGREP_MCP_BINARY` at a small `.cmd` wrapper
    instead: `CreateProcess` has documented special-case handling for `.bat`/
    `.cmd` files (it re-execs them through `cmd.exe /c`), so the wrapper is
    directly spawnable the same way the real `colgrep.exe` would be. The
    wrapper lives under the test's own `tmp_path` rather than next to
    `fake_colgrep.py` so nothing generated leaks into the source tree.
    """
    script = HERE / "fake_colgrep.py"
    if sys.platform == "win32":
        wrapper = tmp_path / "fake_colgrep.cmd"
        wrapper.write_text(f'@echo off\r\n"{sys.executable}" "{script}" %*\r\nexit /b %ERRORLEVEL%\r\n')
        return str(wrapper)
    script.chmod(0o755)
    return str(script)


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
