"""Read-only loopback server. No browser sessions, upstream fetches or sends."""
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
from urllib.parse import unquote, urlsplit

from ff_core import csv_report, markdown_report, workspace_state

VIEWER = Path(__file__).resolve().parents[1] / "assets/viewer"


def make_server(workspace, port):
    state = workspace_state(workspace)  # Fail before opening a socket.
    assets = {"/": VIEWER / "index.html"}
    assets.update({"/" + p.relative_to(VIEWER).as_posix(): p for p in VIEWER.rglob("*") if p.is_file() and not p.is_symlink()})

    class Handler(BaseHTTPRequestHandler):
        server_version = "FlatFinder"
        sys_version = ""

        def log_message(self, *_):
            pass  # Avoid logging private source URLs or phone data.

        def do_GET(self):
            hosts = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            host = self.headers.get("Host", "")
            origin = self.headers.get("Origin")
            if host not in hosts or (origin and origin != f"http://{host}") or self.headers.get("Sec-Fetch-Site") == "cross-site":
                return self.respond(403, b"Forbidden", "text/plain")
            path = unquote(urlsplit(self.path).path)
            if "\\" in path or ".." in path.split("/") or "\x00" in path:
                return self.respond(404, b"Not found", "text/plain")
            try:
                if path in {"/api/state", "/api/export.csv", "/api/report.md"}:
                    current = workspace_state(workspace)
                    if path == "/api/state":
                        return self.respond(200, json.dumps(current, ensure_ascii=False).encode(), "application/json")
                    if path.endswith(".csv"):
                        return self.respond(200, csv_report(current).encode(), "text/csv", "shortlist.csv")
                    return self.respond(200, markdown_report(current, True).encode(), "text/markdown", "shortlist.md")
                if path in assets:
                    return self.respond(200, assets[path].read_bytes(), mimetypes.guess_type(path)[0] or "text/html")
            except (OSError, ValueError, TypeError, KeyError, AttributeError):
                return self.respond(503, b"Local workspace could not be validated. Check it in Codex.", "text/plain")
            return self.respond(404, b"Not found", "text/plain")

        def do_POST(self):
            self.respond(405, b"Read-only viewer", "text/plain")

        do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_POST

        def respond(self, status, body, kind, attachment=None):
            self.send_response(status)
            self.send_header("Content-Type", kind + ("; charset=utf-8" if kind.startswith("text/") or kind == "application/json" else ""))
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://tile.openstreetmap.org; connect-src 'self'; font-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; object-src 'none'")
            if attachment:
                self.send_header("Content-Disposition", f'attachment; filename="{attachment}"')
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server


def serve(workspace, port=43126, demo=False):
    if not 1024 <= port <= 65535:
        raise ValueError("Use an unprivileged port")
    with tempfile.TemporaryDirectory(prefix="flat-finder-demo-") as temp:
        if demo:
            from flat_finder import init_workspace
            workspace = Path(temp)
            init_workspace(workspace, demo=True)
        server = make_server(workspace, port)
        print(f"Flat Finder: http://127.0.0.1:{server.server_port} — {'synthetic demo' if demo else 'private workspace'}. Ctrl-C to stop.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
