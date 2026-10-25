"""Run the COSMOS CONNECT site and MCP server."""

from __future__ import annotations

import os

from .server import serve


def main() -> None:
    port_env = os.environ.get("PORT") or os.environ.get("COSMOS_CONNECT_PORT") or "8787"
    host = os.environ.get("COSMOS_CONNECT_HOST") or ("0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")
    port = int(port_env)
    server = serve(host, port)
    print(f"COSMOS CONNECT http://{host}:{port}/  mcp=/mcp  owner=disabled", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
