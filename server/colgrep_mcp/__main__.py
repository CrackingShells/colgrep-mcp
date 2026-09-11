"""Console entry point: `colgrep-mcp [--transport stdio|streamable-http] [--host H] [--port P]`."""

from __future__ import annotations

import argparse
import logging
import sys

from .config import Settings
from .server import build


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="colgrep-mcp", description=__doc__)
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    logging.basicConfig(level=settings.log_level, stream=sys.stderr, format="%(levelname)s %(name)s: %(message)s")

    server = build()
    if args.transport == "stdio":
        server.run("stdio")
    else:
        server.run("streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":  # pragma: no cover
    main()
