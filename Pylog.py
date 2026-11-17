"""Local dev server: python Pylog.py  ->  http://127.0.0.1:8000
On Vercel, public/ is served statically and api/analyze.py is the function."""
import json
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
<<<<<<< HEAD
from urllib.parse import unquote, urlparse

from pylog_core import analyse_stream
=======
from urllib.parse import urlparse

from pylog_core import analyse_log
>>>>>>> 6b2d266f97b8c34dd8b57158a17acf32bffbb62b

STATIC_DIR = Path(__file__).parent / "public"


class RequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def send_json(self, status_code, payload):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if urlparse(self.path).path != "/api/analyze":
            self.send_error(404, "Not found")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
<<<<<<< HEAD
            if length <= 0:
                raise ValueError("A text log file is required.")
            file_name = unquote(self.headers.get("X-File-Name") or "") or "server.log"
            self.send_json(200, analyse_stream(self.rfile, length, file_name))
        except ValueError as error:
=======
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            text = payload.get("content")
            if not isinstance(text, str):
                raise ValueError("A text log file is required.")
            self.send_json(200, analyse_log(text, str(payload.get("fileName") or "server.log")))
        except (json.JSONDecodeError, ValueError) as error:
>>>>>>> 6b2d266f97b8c34dd8b57158a17acf32bffbb62b
            self.send_json(400, {"error": str(error)})


def main():
    print("Log Analyzer running at http://127.0.0.1:8000")
    threading.Timer(0.5, lambda: webbrowser.open("http://127.0.0.1:8000")).start()
    ThreadingHTTPServer(("127.0.0.1", 8000), RequestHandler).serve_forever()


if __name__ == "__main__":
    main()
