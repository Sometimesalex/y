#!/usr/bin/env python3

import json
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "127.0.0.1"
PORT = 8765

class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        return

    def do_POST(self):
        if self.path != "/querycorpora/":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")

        try:
            payload = json.loads(body)
            question = payload.get("question", "")
        except Exception:
            self.send_response(400)
            self.end_headers()
            return

        # Run producer (writes querycorpora/*.json)
        subprocess.run(
            ["python3", "scripts/query_v2.py", question],
            capture_output=True,
            text=True
        )

        # Run interpreter (reads newest json)
        i = subprocess.run(
            ["python3", "scripts/interpreter.py"],
            capture_output=True,
            text=True
        )

        out = json.dumps({"message": i.stdout})

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(out.encode())


if __name__ == "__main__":
    print(f"Listening on http://{HOST}:{PORT}")
    HTTPServer((HOST, PORT), Handler).serve_forever()
