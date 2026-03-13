from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer

from .backtest import BacktestEngine
from .demo import build_demo_dataset
from .reporting import render_dashboard


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        engine = BacktestEngine()
        result = engine.run(build_demo_dataset())
        html = render_dashboard(result).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = HTTPServer((host, port), DashboardHandler)
    print(f"Dashboard available at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
