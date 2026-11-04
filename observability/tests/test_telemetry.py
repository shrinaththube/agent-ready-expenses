import json
import sys
import threading
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mini_collector  # noqa: E402
import viewer  # noqa: E402


def a(**kw):
    return [{"key": k, "value": ({"intValue": str(v)} if isinstance(v, int) and not isinstance(v, bool) else {"stringValue": str(v)})} for k, v in kw.items()]


def log(ts, event, **kw):
    return {"timeUnixNano": str(ts), "attributes": a(**{"event.name": event, "session.id": "sess-1", **kw})}


RES = a(**{"service.name": "claude-code", "eval.run_id": "r1", "eval.task": "fx-wrong-date-bug", "eval.mode": "with-context",
           "eval.trial": 0, "eval.tags": "fx+python+bug"})
LOGS = {"resourceLogs": [{"resource": {"attributes": RES}, "scopeLogs": [{"logRecords": [
    log(1_000_000_000, "claude_code.tool_result", tool_name="Read", success="true"),
    log(2_000_000_000, "claude_code.tool_result", tool_name="Grep", success="true"),
    log(3_000_000_000, "claude_code.tool_result", tool_name="Edit", success="true"),
    log(4_000_000_000, "claude_code.tool_result", tool_name="Bash", success="false"),
    log(5_000_000_000, "claude_code.api_request", input_tokens=1200, output_tokens=300, cost_usd="0.02"),
]}]}]}


def test_collector_to_viewer_roundtrip(tmp_path):
    out = tmp_path / "t.jsonl"
    srv = mini_collector.make_server(0, out)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    req = urllib.request.Request(f"http://127.0.0.1:{srv.server_address[1]}/v1/logs", data=json.dumps(LOGS).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    assert urllib.request.urlopen(req).status == 200
    srv.shutdown()

    results = tmp_path / "r.jsonl"
    results.write_text(json.dumps({"run_id": "r1", "task": "fx-wrong-date-bug", "mode": "with-context", "trial": 0, "passed": True}) + "\n")
    sess, agg = viewer.build(out, results)
    s = sess["sess-1"]
    assert (s["orientation_cost"], s["tool_calls"], s["loops"], s["tokens"], s["passed"]) == (2, 4, 1, 1500, True)
    assert s["task"] == "fx-wrong-date-bug" and s["tags"] == ["fx", "python", "bug"]
    fx = next(r for r in agg if r["tag"] == "fx")
    assert fx["success_rate"] == 1.0 and fx["tokens_per_success"] == 1500
    assert "fx-wrong-date-bug" in viewer.text(sess, agg)


def test_metrics_fallback_for_tokens(tmp_path):
    doc = {"resourceMetrics": [{"resource": {"attributes": RES}, "scopeMetrics": [{"metrics": [
        {"name": "claude_code.token.usage", "sum": {"dataPoints": [
            {"asInt": "900", "timeUnixNano": "1", "attributes": a(**{"session.id": "s2", "type": "input"})},
            {"asInt": "100", "timeUnixNano": "2", "attributes": a(**{"session.id": "s2", "type": "output"})},
            {"asInt": "5000", "timeUnixNano": "3", "attributes": a(**{"session.id": "s2", "type": "cacheRead"})}]}}]}]}]}
    p = tmp_path / "m.jsonl"
    p.write_text(json.dumps({"signal": "metrics", "payload": doc}) + "\n")
    assert viewer.sessions(list(viewer.records(p)))["s2"]["tokens"] == 1000
