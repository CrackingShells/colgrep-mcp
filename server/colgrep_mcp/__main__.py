"""Console entry point: `colgrep-mcp [--transport stdio|streamable-http] [--host H] [--port P]`."""

from __future__ import annotations

import argparse
import logging
import sys
import warnings

from mcp.shared.exceptions import MCPDeprecationWarning

from . import __version__
from .config import Settings
from .server import build

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="colgrep-mcp", description=__doc__)
    parser.add_argument("--version", action="version", version=f"colgrep-mcp {__version__}")
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    try:
        settings = Settings.from_env()
    except ValueError as exc:
        # A malformed `COLGREP_MCP_TIMEOUT`/`COLGREP_MCP_TEXT_BUDGET` must
        # fail fast with a one-line, readable diagnostic on stderr — not a
        # raw traceback as the operator's only clue (R01 §Configuration).
        print(f"colgrep-mcp: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    # Never let logging land on stdout: on the stdio transport, stdout is the
    # JSON-RPC channel itself, and anything else written there corrupts it.
    logging.basicConfig(level=settings.log_level, stream=sys.stderr, format="%(levelname)s %(name)s: %(message)s")
    logger.info(
        "colgrep-mcp %s starting: binary=%s root=%s timeout_s=%s",
        __version__,
        settings.binary,
        settings.root,
        settings.timeout_s,
    )

    # The logging capability (Context.log / on_set_logging_level) is deprecated
    # as of 2026-07-28 (SEP-2577); the SDK warns at runtime whenever it is
    # exercised. Nothing in this server relies on it, but the warning would
    # otherwise land on stderr indistinguishable from a real problem, so it is
    # silenced here rather than in library code.
    warnings.filterwarnings("ignore", category=MCPDeprecationWarning)

    server = build()
    if args.transport == "stdio":
        server.run("stdio")
    else:
        server.run("streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":  # pragma: no cover
    main()
