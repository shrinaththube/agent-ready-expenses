#!/usr/bin/env python3
"""Minimal OTLP/HTTP JSON receiver: appends every POST body (one JSON document per line) to a file.

Use it when you do not want to run the Docker collector:
  python3 observability/mini_collector.py --port 4318 --out observability/data/telemetry.jsonl
and point Claude Code at it with OTEL_EXPORTER_OTLP_PROTOCOL=http/json
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318. Output format matches the collector's file exporter.
"""
import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LOCK = threading.Lock()


def make_server(port: int, out: Path) -> ThreadingHTTPServer:
    out.parent.mkdir(parents=True, exist_ok=True)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            try:
                doc = json.loads(body)
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                return
            signal = self.path.rsplit("/", 1)[-1]  # logs | metrics | traces
            with LOCK, out.open("a") as f:
                f.write(json.dumps({"signal": signal, "payload": doc}) + "\n")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *a):
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=4318)
    ap.add_argument("--out", type=Path, default=Path("observability/data/telemetry.jsonl"))
    a = ap.parse_args()
    srv = make_server(a.port, a.out)
    print(f"listening on :{srv.server_address[1]} -> {a.out}")
    srv.serve_forever()
