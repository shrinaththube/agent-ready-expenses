#!/usr/bin/env python3
"""End-to-end smoke test: start both services, run the full expense flow, stop them.

receipt text -> parse -> FX convert (expense-date rate) -> create -> submit -> policy decision
-> approve (by a different manager) -> reimburse -> report -> audit trail.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY, RECEIPTS = "http://127.0.0.1:18081", "http://127.0.0.1:18082"


def call(method, url, body=None, actor=None):
    h = {"Content-Type": "application/json"}
    if actor:
        h["X-Actor-ID"], h["X-Actor-Role"] = actor
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.load(r)


def wait(url):
    for _ in range(50):
        try:
            urllib.request.urlopen(url, timeout=1)
            return
        except Exception:
            time.sleep(0.2)
    sys.exit(f"service did not start: {url}")


def main():
    tmp = tempfile.mkdtemp()
    binary = os.path.join(tmp, "policy")
    subprocess.run(["go", "build", "-o", binary, "./cmd/policy"], cwd=ROOT / "services/policy", check=True)
    procs = [
        subprocess.Popen([binary], cwd=ROOT / "services/policy", env={**os.environ, "POLICY_ADDR": "127.0.0.1:18081"}),
        subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", "18082", "--log-level", "warning"], cwd=ROOT / "services/receipts"),
    ]
    try:
        wait(POLICY + "/policies")
        wait(RECEIPTS + "/health")
        text = (ROOT / "fixtures/receipts/dinner-usd.txt").read_text()
        parsed = call("POST", RECEIPTS + "/receipts/parse", {"text": text})
        assert parsed["total"] == {"amount_minor": 8235, "currency": "USD"}, parsed
        quote = call("POST", RECEIPTS + "/fx/convert", {"amount_minor": 10000, "source": "EUR", "date": "2024-03-15"})
        assert quote["target"]["amount_minor"] == 10870, quote
        e1 = ("e1", "employee")
        exp = call("POST", POLICY + "/expenses", {
            "employee_id": "e1", "manager_id": "m1", "category": "meals", "description": parsed["merchant"],
            "amount": parsed["total"], "base_amount": parsed["total"], "date": parsed["date"],
            "has_receipt": True, "attendees": 1, "region": "domestic"})
        out = call("POST", f"{POLICY}/expenses/{exp['id']}/submit", actor=e1)
        assert out["decision"]["outcome"] == "pending_manager", out  # $82.35 > $75 meal cap
        call("POST", f"{POLICY}/expenses/{exp['id']}/approve", {"reason": "ok"}, actor=("m2", "manager"))
        call("POST", f"{POLICY}/expenses/{exp['id']}/reimburse", actor=("f1", "finance"))
        report = call("GET", POLICY + "/reports")
        assert report["rows"][0]["total"] == {"amount_minor": 8235, "currency": "USD"}, report
        trail = call("GET", f"{POLICY}/expenses/{exp['id']}/audit")
        assert [t["to_status"] for t in trail] == ["submitted", "pending_manager", "approved", "reimbursed"], trail
        print("e2e ok:", exp["id"], "->", " -> ".join(t["to_status"] for t in trail))
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            p.wait(timeout=5)


if __name__ == "__main__":
    main()
