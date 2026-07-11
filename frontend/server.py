"""Standalone development server for the Mozhi frontend."""

from __future__ import annotations

import http.server
import mimetypes
import os
import socketserver


mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")

FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "8080"))
FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def guess_type(self, path: str) -> str:
        if path.endswith(".js") or path.endswith(".mjs"):
            return "application/javascript"
        return super().guess_type(path)


def main() -> None:
    """Serve frontend assets only; the API must run as a separate process."""
    os.chdir(FRONTEND_DIR)
    with socketserver.TCPServer(("", FRONTEND_PORT), Handler) as server:
        print(f">>> Frontend serving at http://127.0.0.1:{FRONTEND_PORT}")
        print(">>> Backend API is separate: start it from backend/ on port 8000.")
        print(">>> Press Ctrl+C to stop the frontend.\n")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n>>> Shutting down frontend server.")


if __name__ == "__main__":
    main()
