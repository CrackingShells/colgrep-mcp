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


@pytest.fixture
def fake_store(monkeypatch, tmp_path):
    """A synthetic colgrep index store under `tmp_path`, wired to the fake binary.

    Returns `add(name, project, *, search_count=0, files=3, age_days=0, model=...)`,
    which writes `<store>/<name>/{project.json,state.json,index/}` the way colgrep
    lays them out (index_housekeeping R02) and back-dates `state.json` by
    `age_days`. `project` is any path string: pass one that exists for a live
    project, one that does not for an orphan.
    """
    import json
    import os
    import time

    store = tmp_path / "indices"
    store.mkdir()
    monkeypatch.setenv("FAKE_COLGREP_STORE", str(store))

    def add(name, project, *, search_count=0, files=3, age_days=0, model="lightonai/LateOn-Code-edge"):
        d = store / name
        (d / "index").mkdir(parents=True)
        (d / "index" / "blob").write_bytes(b"x" * 1024)
        (d / "project.json").write_text(
            json.dumps({"project_path": str(project), "project_name": name, "model": model}), encoding="utf-8"
        )
        state = d / "state.json"
        state.write_text(
            json.dumps(
                {
                    "cli_version": "1.6.2",
                    "index_format_version": 2,
                    "files": {f"f{i}.py": {"content_hash": i, "mtime": 0, "size": 1} for i in range(files)},
                    "ignored_files": {},
                    "search_count": search_count,
                    "dirty": False,
                }
            ),
            encoding="utf-8",
        )
        if age_days:
            then = time.time() - age_days * 86400
            os.utime(state, (then, then))
        return d

    add.root = store
    return add
