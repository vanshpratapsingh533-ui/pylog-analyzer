import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pylog_core import analyse_stream  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def send_json(self, status_code, payload):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                raise ValueError("A text log file is required.")
            file_name = unquote(self.headers.get("X-File-Name") or "") or "server.log"
            self.send_json(200, analyse_stream(self.rfile, length, file_name))
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
        except Exception:
            self.send_json(500, {"error": "Something went wrong while reading the log."})

    def do_GET(self):
        self.send_json(405, {"error": "Use POST."})
