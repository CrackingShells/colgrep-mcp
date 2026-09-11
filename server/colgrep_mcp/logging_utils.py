"""Best-effort client logging (R05 M2: notifications/message may be unsupported)."""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("colgrep_mcp")


async def safe_log(ctx: Any, level: str, message: str) -> None:
    """Send a log notification to the client; never let a failure surface."""
    try:
        fn = getattr(ctx, level)
        await fn(message)
    except Exception:  # noqa: BLE001 - logging must never break a tool
        log.debug("client log dropped (%s): %s", level, message)
