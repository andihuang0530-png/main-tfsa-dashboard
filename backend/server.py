from __future__ import annotations

import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import services
from storage.json_store import ROOT_DIR


FRONTEND_DIR = ROOT_DIR / "frontend"


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


class Handler(BaseHTTPRequestHandler):
    server_version = "TFSAResearchMVP/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path.startswith("/api/"):
                self.handle_get_api(parsed.path, parse_qs(parsed.query))
            else:
                self.serve_static(parsed.path)
        except ApiError as exc:
            self.send_json({"error": str(exc)}, exc.status)
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            body = self.read_json_body()
            self.handle_post_api(parsed.path, body)
        except ApiError as exc:
            self.send_json({"error": str(exc)}, exc.status)
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)

    def read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def handle_get_api(self, path: str, query: dict[str, list[str]]) -> None:
        app_state = None
        if path == "/api/state":
            app_state = services.state()
            app_state["summaryCards"] = services.summary_cards(app_state)
            self.send_json(app_state)
            return
        if path == "/api/watchlist":
            self.send_json(services.state()["watchlistAnalysis"])
            return
        if path == "/api/weekly-picks":
            self.send_json(services.state()["weeklyPicks"])
            return
        if path == "/api/recommendations":
            self.send_json(services.state()["recommendation"])
            return
        if path == "/api/transactions":
            self.send_json(services.state()["transactions"])
            return
        if path == "/api/holdings":
            state = services.state()
            self.send_json({"holdings": state["holdings"], "summary": state["portfolioSummary"]})
            return
        if path == "/api/settings":
            self.send_json(services.state()["settings"])
            return
        if path == "/api/candidate-universe":
            self.send_json(services.state()["candidateUniverse"])
            return
        if path.startswith("/api/export/"):
            kind = path.removeprefix("/api/export/")
            fmt = query.get("format", ["json"])[0]
            content, content_type = services.export_payload(kind, fmt)
            self.send_text(content, content_type)
            return
        raise ApiError("Endpoint not found.", 404)

    def handle_post_api(self, path: str, body: dict) -> None:
        if path == "/api/watchlist/add":
            self.send_json(services.add_watchlist_ticker(body.get("ticker", "")))
            return
        if path == "/api/watchlist/remove":
            self.send_json(services.remove_watchlist_ticker(body.get("ticker", "")))
            return
        if path == "/api/watchlist/update":
            self.send_json(services.update_watchlist_ticker(body.get("ticker", ""), body))
            return
        if path == "/api/weekly-picks/add-to-watchlist":
            self.send_json(services.add_watchlist_ticker(body.get("ticker", "")))
            return
        if path == "/api/weekly-picks/dismiss":
            self.send_json(services.dismiss_weekly_pick(body.get("ticker", "")))
            return
        if path == "/api/recommendations/calculate":
            self.send_json(services.calculate_with_overrides(body))
            return
        if path == "/api/transactions/add":
            self.send_json(services.add_transaction(body))
            return
        if path == "/api/transactions/update":
            self.send_json(services.update_transaction(body))
            return
        if path == "/api/transactions/delete":
            self.send_json(services.delete_transaction(body.get("id", "")))
            return
        if path == "/api/holdings/target":
            self.send_json(services.update_watchlist_ticker(body.get("ticker", ""), {"targetAllocation": body.get("targetAllocation")}))
            return
        if path == "/api/settings/update":
            self.send_json(services.update_settings(body))
            return
        if path == "/api/settings/update-universe":
            self.send_json(services.update_candidate_universe(body.get("items", [])))
            return
        raise ApiError("Endpoint not found.", 404)

    def serve_static(self, path: str) -> None:
        if path in {"", "/"}:
            file_path = FRONTEND_DIR / "index.html"
        else:
            safe_path = path.lstrip("/")
            file_path = (FRONTEND_DIR / safe_path).resolve()
            if not str(file_path).startswith(str(FRONTEND_DIR.resolve())):
                raise ApiError("Forbidden.", 403)
        if not file_path.exists() or file_path.is_dir():
            file_path = FRONTEND_DIR / "index.html"
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        payload = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_json(self, payload: object, status: int = 200) -> None:
        raw = json.dumps(payload, indent=2, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def send_text(self, payload: str, content_type: str = "text/plain", status: int = 200) -> None:
        raw = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}")


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"TFSA dashboard MVP running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    import os

    # Cloud hosts (Render, Railway, etc.) provide the port via the PORT env var
    # and require binding to 0.0.0.0. Local runs keep the 127.0.0.1:8000 default.
    port = int(os.environ.get("PORT", "8000"))
    host = "0.0.0.0" if "PORT" in os.environ else "127.0.0.1"
    run(host=host, port=port)
