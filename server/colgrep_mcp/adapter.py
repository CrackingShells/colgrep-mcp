"""Subprocess adapter around the colgrep CLI (R01 §Adapter contract).

Everything that talks to the binary lives here. Tools never spawn processes
themselves; they call this adapter and translate its exceptions into ToolError.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import IndexBuildResult, IndexInfo, IndexStatus

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
    """Async wrapper over the colgrep binary. Implemented in leaf `colgrep_adapter`."""

    def __init__(
        self,
        binary: str = "colgrep",
        timeout_s: float = 600.0,
        on_stderr: StderrCallback | None = None,
    ) -> None:
        self.binary = binary
        self.timeout_s = timeout_s
        self.on_stderr = on_stderr

    def build_search_argv(self, req: SearchRequest) -> list[str]:
        raise NotImplementedError

    async def version(self) -> str:
        raise NotImplementedError

    async def search(self, req: SearchRequest) -> list[RawHit]:
        raise NotImplementedError

    async def status(self, path: Path) -> IndexStatus:
        raise NotImplementedError

    async def stats(self) -> list[IndexInfo]:
        raise NotImplementedError

    async def settings(self) -> dict[str, str]:
        raise NotImplementedError

    async def init(self, path: Path, *, force_cpu: bool = False) -> IndexBuildResult:
        raise NotImplementedError

    async def clear(self, path: Path) -> None:
        raise NotImplementedError
