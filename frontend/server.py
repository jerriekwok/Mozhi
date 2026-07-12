"""Standalone development server for the Mozhi frontend."""

from __future__ import annotations

import http.server
import mimetypes
import os
import socketserver
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")

FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "8080"))
FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")


class Handler(http.server.SimpleHTTPRequestHandler):
    def guess_type(self, path: str) -> str:
        if path.endswith(".js") or path.endswith(".mjs"):
            return "application/javascript"
        return super().guess_type(path)

    def do_GET(self) -> None:
        if self.path.startswith("/glyph-library/"):
            self._proxy_glyph_image()
            return
        super().do_GET()

    def _proxy_glyph_image(self) -> None:
        """Serve glyph images from the backend on the frontend origin for canvas processing."""
        try:
            with urlopen(f"{BACKEND_URL}{self.path}", timeout=10) as response:
                content = response.read()
                self.send_response(response.status)
                self.send_header("Content-Type", response.headers.get_content_type())
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(content)
        except HTTPError as exc:
            self.send_error(exc.code, "Glyph image was not found")
        except URLError:
            self.send_error(502, "Glyph backend is unavailable")


def main() -> None:
    """Serve frontend assets only; the API must run as a separate process."""
    os.chdir(FRONTEND_DIR)
    # Glyph image proxy requests may take a moment.  Use a threaded server so
    # one slow image does not block the browser from loading scripts or switching pages.
    with socketserver.ThreadingTCPServer(("", FRONTEND_PORT), Handler) as server:
        print(f">>> Frontend serving at http://127.0.0.1:{FRONTEND_PORT}")
        print(">>> Backend API is separate: start it from backend/ on port 8000.")
        print(">>> Press Ctrl+C to stop the frontend.\n")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n>>> Shutting down frontend server.")


if __name__ == "__main__":
    main()
