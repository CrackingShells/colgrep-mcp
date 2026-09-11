"""Runtime configuration read from environment variables (see R01 §Configuration)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


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
    def from_env(cls, env: dict[str, str] | None = None) -> "Settings":
        e = os.environ if env is None else env
        root_raw = e.get("COLGREP_MCP_ROOT")
        return cls(
            binary=e.get("COLGREP_MCP_BINARY", "colgrep"),
            root=Path(root_raw).expanduser() if root_raw else None,
            timeout_s=float(e.get("COLGREP_MCP_TIMEOUT", "600")),
            text_budget=int(e.get("COLGREP_MCP_TEXT_BUDGET", "12000")),
            log_level=e.get("COLGREP_MCP_LOG_LEVEL", "INFO"),
        )
