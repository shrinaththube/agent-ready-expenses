#!/usr/bin/env python3
"""Egress proxy for the agent sandbox.

* Allowlist only: any host not in the allowlist gets 403 and is logged.
* Holds the real secrets. The sandbox only knows placeholders; on allowed hosts the proxy swaps
  placeholder -> real value in request headers and bodies, and real -> placeholder in responses.
* Logs every request (allowed, blocked, tunnelled) as JSON lines.

Allowlist line: `<host[:port]> [upstream=http|https] [tunnel]`. `tunnel` allows CONNECT (HTTPS passthrough,
no inspection, no secret swap). Plain-HTTP requests to the proxy are the swappable path: the proxy speaks
https upstream when `upstream=https`.
"""
import argparse
import http.client
import json
import os
import select
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOP = {"connection", "proxy-connection", "keep-alive", "transfer-encoding", "te", "upgrade", "proxy-authorization", "content-length", "host"}


class Policy:
    def __init__(self, allow_lines, secrets, resolve=None):
        self.hosts = {}
        for ln in allow_lines:
            ln = ln.split("#")[0].strip()
            if not ln:
                continue
            host, *opts = ln.split()
            self.hosts[host] = {"upstream": "http", "tunnel": False}
            for o in opts:
                if o == "tunnel":
                    self.hosts[host]["tunnel"] = True
                elif o.startswith("upstream="):
                    self.hosts[host]["upstream"] = o.split("=", 1)[1]
        self.secrets = secrets  # placeholder -> real
        self.resolve = resolve or {}  # host -> (ip, port) override, used by tests/demo

    def lookup(self, hostport: str):
        host = hostport.split(":")[0]
        return self.hosts.get(hostport) or self.hosts.get(host)

    def swap_out(self, data: bytes) -> bytes:
        for ph, real in self.secrets.items():
            data = data.replace(ph.encode(), real.encode())
        return data

    def swap_back(self, data: bytes) -> bytes:
        for ph, real in self.secrets.items():
            data = data.replace(real.encode(), ph.encode())
        return data


def make_server(port: int, policy: Policy, log_path: Path) -> ThreadingHTTPServer:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()

    def log(**kw):
        kw["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        with lock, log_path.open("a") as f:
            f.write(json.dumps(kw) + "\n")

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def _deny(self, host, why):
            log(action="blocked", method=self.command, host=host, path=self.path, reason=why)
            body = json.dumps({"error": "egress blocked", "host": host, "reason": why}).encode()
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _forward(self):
            from urllib.parse import urlsplit
            u = urlsplit(self.path)
            hostport = u.netloc or self.headers.get("Host", "")
            rule = policy.lookup(hostport)
            if rule is None:
                return self._deny(hostport, "host not in allowlist")
            n = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(n) if n else b""
            body = policy.swap_out(raw)
            raw_headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP}
            headers = {k: policy.swap_out(v.encode()).decode() for k, v in raw_headers.items()}
            swapped = body != raw or headers != raw_headers
            host = hostport.split(":")[0]
            ip, uport = policy.resolve.get(host, (host, int(hostport.split(":")[1]) if ":" in hostport else (443 if rule["upstream"] == "https" else 80)))
            conn_cls = http.client.HTTPSConnection if rule["upstream"] == "https" else http.client.HTTPConnection
            conn = conn_cls(ip, uport, timeout=15)
            try:
                conn.request(self.command, (u.path or "/") + (f"?{u.query}" if u.query else ""), body=body or None, headers={**headers, "Host": hostport})
                r = conn.getresponse()
                data = policy.swap_back(r.read())
            except OSError as e:
                log(action="error", method=self.command, host=hostport, path=u.path, reason=str(e))
                return self._deny(hostport, f"upstream error: {e}")
            log(action="allowed", method=self.command, host=hostport, path=u.path, status=r.status, secret_swapped=swapped)
            self.send_response(r.status)
            for k, v in r.getheaders():
                if k.lower() not in HOP:
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _forward

        def do_CONNECT(self):
            rule = policy.lookup(self.path)
            if rule is None or not rule["tunnel"]:
                return self._deny(self.path, "CONNECT not allowed for host")
            host, _, port = self.path.partition(":")
            try:
                up = socket.create_connection((host, int(port or 443)), timeout=15)
            except OSError as e:
                return self._deny(self.path, f"upstream error: {e}")
            log(action="tunnel", method="CONNECT", host=self.path)
            self.send_response(200, "Connection established")
            self.end_headers()
            socks = [self.connection, up]
            while True:
                r, _, _ = select.select(socks, [], [], 30)
                if not r:
                    break
                for s in r:
                    d = s.recv(65536)
                    if not d:
                        up.close()
                        return
                    (up if s is self.connection else self.connection).sendall(d)

        def log_message(self, *a):
            pass

    return ThreadingHTTPServer(("0.0.0.0" if os.environ.get("PROXY_BIND_ALL") else "127.0.0.1", port), H)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--allowlist", type=Path, default=Path(__file__).parent / "allowlist.txt")
    ap.add_argument("--log", type=Path, default=Path("sandbox/logs/egress.jsonl"))
    a = ap.parse_args()
    # Real secrets come from the proxy's own environment: PLACEHOLDER_<NAME>=<placeholder>, REAL_<NAME>=<secret>
    secrets = {os.environ[k]: os.environ["REAL_" + k.removeprefix("PLACEHOLDER_")]
               for k in os.environ if k.startswith("PLACEHOLDER_") and "REAL_" + k.removeprefix("PLACEHOLDER_") in os.environ}
    srv = make_server(a.port, Policy(a.allowlist.read_text().splitlines(), secrets), a.log)
    print(f"egress proxy on :{a.port}, {len(secrets)} secret(s) held, log -> {a.log}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
