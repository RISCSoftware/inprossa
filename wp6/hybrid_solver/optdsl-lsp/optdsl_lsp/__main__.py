"""Console entry point for the OptDSL language server."""

from __future__ import annotations

import argparse
import logging

from .server import SERVER_NAME, SERVER_VERSION, server


def main() -> None:
    parser = argparse.ArgumentParser(prog=SERVER_NAME, description="OptDSL language server")
    parser.add_argument("--version", action="version", version=f"{SERVER_NAME} {SERVER_VERSION}")
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="communicate over stdio (the default; accepted for LSP client compatibility)",
    )
    parser.add_argument(
        "--node-ipc",
        action="store_true",
        help="accepted for compatibility; not supported, falls back to stdio",
    )
    parser.add_argument(
        "--tcp",
        type=int,
        default=None,
        metavar="PORT",
        help="listen on a TCP port instead of stdio (useful for debugging)",
    )
    parser.add_argument("--log-level", default="INFO", help="logging level (default: INFO)")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # `vscode-languageclient` appends `--stdio` unconditionally when the
    # transport is TransportKind.stdio, so the flag must be accepted even
    # though stdio is already the default. Rejecting it makes the client
    # crash-loop with "unrecognized arguments: --stdio".
    if args.node_ipc:
        logging.warning("--node-ipc is not supported; falling back to stdio")

    if args.tcp is not None:
        server.start_tcp("127.0.0.1", args.tcp)
    else:
        server.start_io()


if __name__ == "__main__":
    main()
