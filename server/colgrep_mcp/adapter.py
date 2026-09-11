"""Subprocess adapter around the colgrep CLI (R01 §Adapter contract).

Everything that talks to the binary lives here. Tools never spawn processes
themselves; they call this adapter and translate its exceptions into ToolError.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import IndexBuildResult, IndexInfo, IndexStatus
from .textparse import parse_index_summary, parse_settings, parse_stats, parse_status

StderrCallback = Callable[[str], Awaitable[None]]


class ColgrepError(Exception):
    """Base class for adapter failures."""


class ColgrepNotFound(ColgrepError):
    """The colgrep binary could not be executed."""


class ColgrepFailed(ColgrepError):
    """colgrep exited non-zero."""

    def __init__(self, returncode: int, stderr_tail: str, argv: list[str]):
        super().__init__(f"colgrep exited {returncode}: {stderr_tail.strip()[-500:]}")
        self.returncode = returncode
        self.stderr_tail = stderr_tail
        self.argv = argv


class ColgrepTimeout(ColgrepError):
    """colgrep exceeded the configured timeout."""


class ColgrepParseError(ColgrepError):
    """colgrep output could not be parsed."""

    def __init__(self, message: str, raw: str):
        super().__init__(message)
        self.raw = raw


@dataclass
class SearchRequest:
    query: str | None
    paths: list[Path]
    pattern: str | None = None
    fixed_string: bool = False
    whole_word: bool = False
    case_sensitive: bool = False
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    exclude_dir: list[str] = field(default_factory=list)
    limit: int | None = 15
    code_only: bool = False
    semantic_only: bool = False
    alpha: float | None = None
    skip_index_update: bool = False


RawHit = dict[str, Any]


class ColgrepAdapter:
    """Async wrapper over the colgrep binary. Implemented in leaf `colgrep_adapter`.

    Everything that talks to the binary funnels through `_run`: one
    `asyncio.create_subprocess_exec` call (never a shell), stdin closed,
    stdout fully buffered, stderr consumed line-by-line into a bounded tail
    and optionally forwarded to `on_stderr`, the whole call bounded by
    `timeout_s`.
    """

    #: Max stderr lines kept for `ColgrepFailed.stderr_tail` / diagnostics.
    _STDERR_TAIL_LINES = 50

    def __init__(
        self,
        binary: str = "colgrep",
        timeout_s: float = 600.0,
        on_stderr: StderrCallback | None = None,
    ) -> None:
        self.binary = binary
        self.timeout_s = timeout_s
        self.on_stderr = on_stderr
        # Set by `_run` after every spawn; for tests only (proving no zombie
        # process survives a `ColgrepTimeout`), never read by production code.
        self._last_proc: asyncio.subprocess.Process | None = None

    def with_stderr(self, on_stderr: StderrCallback | None) -> "ColgrepAdapter":
        """A shallow copy sharing `binary`/`timeout_s` but a different `on_stderr`.

        Used by the server-assembly layer to get a per-call adapter that
        streams progress to a specific tool invocation's `ctx` without
        mutating the shared adapter instance.
        """
        return ColgrepAdapter(binary=self.binary, timeout_s=self.timeout_s, on_stderr=on_stderr)

    def build_search_argv(self, req: SearchRequest) -> list[str]:
        """Pure argv builder for `colgrep search` (no subprocess, no `--color`).

        `_run` is responsible for `--color never`; this only ever returns the
        subcommand-specific argv so it can be unit-tested on its own.
        """
        if req.query is not None and req.query.startswith("-"):
            raise ColgrepError(
                f"query must not start with '-' (would be parsed as a flag): {req.query!r}"
            )

        argv: list[str] = ["search", "--json", "-y"]

        if req.pattern is not None:
            argv += ["-e", req.pattern]
        if req.fixed_string:
            argv.append("-F")
        if req.whole_word:
            argv.append("-w")
        if req.case_sensitive:
            argv.append("-s")
        for pattern in req.include:
            argv += ["--include", pattern]
        for pattern in req.exclude:
            argv += ["--exclude", pattern]
        for name in req.exclude_dir:
            argv += ["--exclude-dir", name]
        if req.limit is not None:
            argv += ["-k", str(req.limit)]
        if req.code_only:
            argv.append("--code-only")
        if req.semantic_only:
            argv.append("--semantic-only")
        if req.alpha is not None:
            argv += ["--alpha", str(req.alpha)]
        if req.skip_index_update:
            argv.append("--no-update")
        if req.query is not None:
            argv.append(req.query)
        argv += [str(p) for p in req.paths]

        return argv

    async def _run(
        self,
        argv: list[str],
        *,
        cwd: Path | str | None = None,
        stream_stderr: bool = False,
    ) -> tuple[str, str, int]:
        """Run `[binary, argv[0], "--color", "never", *argv[1:]]` and collect output.

        `--color never` is always inserted right after the subcommand/flag in
        `argv[0]` — every subcommand the adapter drives (search, status,
        clear, init, settings) as well as the top-level `--stats`/`--version`
        flags accept it there (verified against the real binary).
        """
        full_argv = [argv[0], "--color", "never", *argv[1:]] if argv else ["--color", "never"]
        env = {**os.environ, "NO_COLOR": "1"}

        try:
            proc = await asyncio.create_subprocess_exec(
                self.binary,
                *full_argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
                cwd=str(cwd) if cwd is not None else None,
                env=env,
            )
        except (FileNotFoundError, PermissionError) as exc:
            raise ColgrepNotFound(self.binary) from exc

        self._last_proc = proc  # tests only

        stderr_tail: deque[str] = deque(maxlen=self._STDERR_TAIL_LINES)

        async def _drain_stderr() -> None:
            assert proc.stderr is not None
            async for raw_line in proc.stderr:
                line = raw_line.decode(errors="replace").rstrip("\n")
                stderr_tail.append(line)
                if stream_stderr and self.on_stderr is not None:
                    await self.on_stderr(line)

        async def _drain_stdout() -> bytes:
            assert proc.stdout is not None
            return await proc.stdout.read()

        try:
            stdout_bytes, _stderr_done, _returncode = await asyncio.wait_for(
                asyncio.gather(_drain_stdout(), _drain_stderr(), proc.wait()),
                timeout=self.timeout_s,
            )
        except TimeoutError:
            proc.kill()
            await proc.wait()
            raise ColgrepTimeout(
                f"colgrep timed out after {self.timeout_s}s: {' '.join(full_argv)}"
            ) from None
        except BaseException:
            # Any other abnormal exit from `wait_for` — most importantly the
            # calling task itself being cancelled (`asyncio.CancelledError`,
            # a `BaseException` that `except TimeoutError` never catches) —
            # must still reap the child instead of abandoning it. `wait_for`
            # already cancels-and-awaits the gathered future before this
            # line runs (see `asyncio.tasks.wait_for`), so the stderr-drain
            # coroutine is already finished; only the subprocess itself still
            # needs killing and reaping here.
            proc.kill()
            await proc.wait()
            raise

        stdout = stdout_bytes.decode(errors="replace")
        stderr = "\n".join(stderr_tail)
        returncode = proc.returncode

        if returncode != 0:
            raise ColgrepFailed(returncode, stderr, full_argv)

        return stdout, stderr, returncode

    async def version(self) -> str:
        stdout, _stderr, _rc = await self._run(["--version"])
        return stdout.strip()

    async def search(self, req: SearchRequest) -> list[RawHit]:
        for p in req.paths:
            if not p.is_absolute():
                raise ColgrepError(f"search() requires absolute paths, got {p!r}")

        argv = self.build_search_argv(req)
        stdout, _stderr, _rc = await self._run(argv, stream_stderr=True)

        stripped = stdout.strip()
        if not stripped:
            # R03 D6: zero hits is `[]`, not empty stdout, but tolerate an
            # empty stream the same way rather than treat it as a parse bug.
            return []

        try:
            data = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ColgrepParseError(f"colgrep search stdout was not valid JSON: {exc}", stdout) from exc

        if not isinstance(data, list):
            raise ColgrepParseError("colgrep search stdout was valid JSON but not a list", stdout)

        return data

    async def status(self, path: Path) -> IndexStatus:
        if not path.is_absolute():
            raise ColgrepError(f"status() requires an absolute path, got {path!r}")
        stdout, _stderr, _rc = await self._run(["status", str(path)])
        return parse_status(stdout, str(path))

    async def stats(self) -> list[IndexInfo]:
        stdout, _stderr, _rc = await self._run(["--stats"])
        return parse_stats(stdout)

    async def settings(self) -> dict[str, str]:
        stdout, _stderr, _rc = await self._run(["settings"])
        return parse_settings(stdout)

    async def init(self, path: Path, *, force_cpu: bool = False) -> IndexBuildResult:
        if not path.is_absolute():
            raise ColgrepError(f"init() requires an absolute path, got {path!r}")

        argv = ["init", "-y", *(["--force-cpu"] if force_cpu else []), str(path)]
        start = time.monotonic()
        _stdout, stderr, _rc = await self._run(argv, stream_stderr=True)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        # R05 D2: no per-file progress on stderr, just a banner and exactly
        # one summary line (either shape) — take the first one found.
        summary = next(
            (s for s in (parse_index_summary(line) for line in stderr.splitlines()) if s is not None),
            None,
        )
        log_tail = stderr.splitlines()[-20:]

        return IndexBuildResult(
            project=summary.root if summary is not None else str(path),
            units_indexed=None,
            elapsed_ms=elapsed_ms,
            log_tail=log_tail,
            added=summary.added if summary is not None else None,
            changed=summary.changed if summary is not None else None,
            deleted=summary.deleted if summary is not None else None,
            unchanged=summary.unchanged if summary is not None else None,
            up_to_date=summary.up_to_date if summary is not None else False,
        )

    async def clear(self, path: Path) -> None:
        if not path.is_absolute():
            raise ColgrepError(f"clear() requires an absolute path, got {path!r}")
        await self._run(["clear", str(path)])
