"""Runtime configuration read from environment variables (see R01 §Configuration)."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Settings:
    """Environment-derived settings. Construct with :func:`Settings.from_env`."""

    binary: str = "colgrep"
    root: Path | None = None
    timeout_s: float = 600.0
    text_budget: int = 12_000
    log_level: str = "INFO"
    extra_env: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Settings:
        e = os.environ if env is None else env
        root_raw = e.get("COLGREP_MCP_ROOT")
        return cls(
            binary=e.get("COLGREP_MCP_BINARY", "colgrep"),
            root=Path(root_raw).expanduser() if root_raw else None,
            timeout_s=_parse_numeric_env(e, "COLGREP_MCP_TIMEOUT", "600", float),
            text_budget=_parse_numeric_env(e, "COLGREP_MCP_TEXT_BUDGET", "12000", int),
            log_level=e.get("COLGREP_MCP_LOG_LEVEL", "INFO"),
        )


def _parse_numeric_env(env: dict[str, str], name: str, default: str, cast: Callable[[str], Any]) -> Any:
    """`cast(env.get(name, default))`, re-raising a malformed value as a
    `ValueError` that names the offending variable.

    A bare `float()`/`int()` failure ("could not convert string to float:
    'abc'") never says *which* environment variable was wrong; `main()`
    turns this into the process's only diagnostic on a bad value (R01
    §Configuration), so it must be readable on its own, not just a
    traceback.
    """
    raw = env.get(name, default)
    try:
        return cast(raw)
    except ValueError as exc:
        raise ValueError(f"invalid {name}={raw!r}: must be a number") from exc
