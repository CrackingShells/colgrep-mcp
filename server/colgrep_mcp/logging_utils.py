"""The only module a tool notifies the client through (R01 §C4): log messages,
progress, resource-updated.

Every function here has the same contract: try to tell the client, and if the
client (or the transport, or the SDK's deprecation of the capability) refuses,
record the drop at debug level and return — a notification must never turn a
succeeding tool call into a failing one (R05 M2).
"""

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


async def safe_progress(ctx: Any, progress: float, total: float | None, message: str) -> None:
    """`ctx.report_progress(...)`; never let a failure surface."""
    try:
        await ctx.report_progress(progress, total=total, message=message)
    except Exception:  # noqa: BLE001 - progress must never break a tool
        log.debug("client progress dropped: %s", message)


async def safe_notify_resource_updated(ctx: Any, uri: str) -> None:
    """`ctx.notify_resource_updated(uri)`; never let a failure surface."""
    try:
        await ctx.notify_resource_updated(uri)
    except Exception:  # noqa: BLE001 - resource-update notification is best-effort
        log.debug("client resource-updated notification dropped: %s", uri)
