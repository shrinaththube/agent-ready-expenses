#!/usr/bin/env python3
"""Summarise Claude Code OpenTelemetry data (OTLP JSON lines) per session and per eval tag.

  viewer.py observability/data/telemetry.jsonl
  viewer.py data.jsonl --results evals/results/run.jsonl --html out.html
  viewer.py data.jsonl --serve 8088

Metrics per session
  orientation cost  tool calls before the first Edit/Write (how long the agent reads before acting)
  loops             failed tool calls (the agent retrying)
  tokens, cost      from claude_code.api_request log events
Aggregates (needs --results to know pass/fail)
  success by tag, tokens per success
Input lines are either {"signal", "payload"} (mini_collector) or raw OTLP JSON (collector file exporter).
"""
import argparse
import html
import json
import sys
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def val(v: dict):
    for k in ("stringValue", "intValue", "doubleValue", "boolValue"):
        if k in v:
            return int(v[k]) if k == "intValue" else v[k]
    return None


def attrs(lst) -> dict:
    return {a["key"]: val(a["value"]) for a in lst or []}


def records(path: Path):
    """Yield flat dicts: {kind, name, ts, value, **attrs} with resource attributes merged in."""
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        doc = json.loads(line)
        doc = doc.get("payload", doc)
        for rl in doc.get("resourceLogs", []):
            res = attrs(rl.get("resource", {}).get("attributes"))
            for sl in rl.get("scopeLogs", []):
                for lr in sl.get("logRecords", []):
                    a = attrs(lr.get("attributes"))
                    yield {"kind": "log", "name": a.get("event.name", ""), "ts": int(lr.get("timeUnixNano", 0)), "value": None, **res, **a}
        for rm in doc.get("resourceMetrics", []):
            res = attrs(rm.get("resource", {}).get("attributes"))
            for sm in rm.get("scopeMetrics", []):
                for m in sm.get("metrics", []):
                    for dp in (m.get("sum") or m.get("gauge") or {}).get("dataPoints", []):
                        v = dp.get("asInt", dp.get("asDouble", 0))
                        yield {"kind": "metric", "name": m["name"], "ts": int(dp.get("timeUnixNano", 0)), "value": float(v), **res, **attrs(dp.get("attributes"))}


def sessions(recs) -> dict:
    by = defaultdict(list)
    for r in recs:
        by[r.get("session.id", "unknown")].append(r)
    out = {}
    for sid, rs in by.items():
        rs.sort(key=lambda r: r["ts"])
        tools = [r for r in rs if r["name"].endswith("tool_result")]
        first_edit = next((i for i, r in enumerate(tools) if r.get("tool_name") in EDIT_TOOLS), None)
        reqs = [r for r in rs if r["name"].endswith("api_request")]
        tok = sum(int(r.get("input_tokens", 0)) + int(r.get("output_tokens", 0)) for r in reqs)
        if not reqs:  # fall back to the token.usage metric
            tok = int(sum(r["value"] for r in rs if r["name"].endswith("token.usage") and r.get("type") in ("input", "output")))
        meta = next((r for r in rs if "eval.task" in r), {})
        out[sid] = {
            "session": sid, "task": meta.get("eval.task"), "mode": meta.get("eval.mode"), "trial": meta.get("eval.trial"),
            "run_id": meta.get("eval.run_id"), "tags": (meta.get("eval.tags") or "").split("+") if meta.get("eval.tags") else [],
            "tool_calls": len(tools), "orientation_cost": first_edit if first_edit is not None else len(tools),
            "edited": first_edit is not None, "loops": sum(1 for r in tools if str(r.get("success")).lower() == "false"),
            "tokens": tok, "cost_usd": round(sum(float(r.get("cost_usd", 0)) for r in reqs), 4),
            "duration_s": round((rs[-1]["ts"] - rs[0]["ts"]) / 1e9, 1) if rs else 0,
        }
    return out


def attach_results(sess: dict, results: list[dict]):
    idx = {(r["run_id"], r["task"], r["mode"], str(r["trial"])): r for r in results}
    for s in sess.values():
        r = idx.get((s["run_id"], s["task"], s["mode"], str(s["trial"])))
        s["passed"] = None if r is None else r["passed"]


def aggregates(sess: dict) -> list[dict]:
    g = defaultdict(list)
    for s in sess.values():
        if s.get("passed") is None:
            continue
        for tag in s["tags"] or ["untagged"]:
            g[(tag, s["mode"])].append(s)
    rows = []
    for (tag, mode), ss in sorted(g.items()):
        ok = [s for s in ss if s["passed"]]
        rows.append({"tag": tag, "mode": mode, "sessions": len(ss), "success_rate": len(ok) / len(ss),
                     "tokens_per_success": (sum(s["tokens"] for s in ss) / len(ok)) if ok else None,
                     "avg_orientation_cost": sum(s["orientation_cost"] for s in ss) / len(ss),
                     "avg_loops": sum(s["loops"] for s in ss) / len(ss)})
    return rows


def text(sess: dict, agg: list[dict]) -> str:
    L = [f"{'session':14} {'task':32} {'mode':13} {'orient':>6} {'calls':>5} {'loops':>5} {'tokens':>8} {'cost$':>7} {'sec':>6} pass"]
    for s in sorted(sess.values(), key=lambda s: (str(s["task"]), str(s["mode"]))):
        L.append(f"{s['session'][:14]:14} {str(s['task'])[:32]:32} {str(s['mode']):13} {s['orientation_cost']:>6} {s['tool_calls']:>5} "
                 f"{s['loops']:>5} {s['tokens']:>8} {s['cost_usd']:>7} {s['duration_s']:>6} {s.get('passed', '-')}")
    if agg:
        L += ["", f"{'tag':14} {'mode':13} {'n':>3} {'success':>8} {'tokens/success':>15} {'orient':>7} {'loops':>6}"]
        for a in agg:
            tps = "n/a" if a["tokens_per_success"] is None else f"{a['tokens_per_success']:.0f}"
            L.append(f"{a['tag']:14} {a['mode']:13} {a['sessions']:>3} {a['success_rate']:>8.0%} {tps:>15} {a['avg_orientation_cost']:>7.1f} {a['avg_loops']:>6.1f}")
    return "\n".join(L)


def page(sess: dict, agg: list[dict]) -> str:
    return ("<!doctype html><meta charset=utf-8><title>Tally agent telemetry</title>"
            "<style>body{font:14px system-ui;margin:2rem}pre{background:#f6f8fa;padding:1rem;overflow:auto}</style>"
            f"<h1>Agent sessions</h1><pre>{html.escape(text(sess, agg))}</pre>")


def build(path: Path, results: Path | None):
    sess = sessions(list(records(path)))
    if results:
        attach_results(sess, [json.loads(line) for line in results.read_text().splitlines() if line.strip()])
    return sess, aggregates(sess)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("telemetry", type=Path)
    ap.add_argument("--results", type=Path)
    ap.add_argument("--html", type=Path)
    ap.add_argument("--serve", type=int)
    a = ap.parse_args()
    if a.serve:
        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                body = page(*build(a.telemetry, a.results)).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *x):
                pass
        print(f"viewer on http://localhost:{a.serve}")
        HTTPServer(("0.0.0.0", a.serve), H).serve_forever()
    sess, agg = build(a.telemetry, a.results)
    if a.html:
        a.html.write_text(page(sess, agg))
    print(text(sess, agg))
    return 0


if __name__ == "__main__":
    sys.exit(main())
