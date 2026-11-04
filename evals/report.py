#!/usr/bin/env python3
"""Summarise eval results.

  report.py results/run1.jsonl [...]                     markdown table, with vs without context
  report.py --readme ../README.md results/*.jsonl        rewrite the table between result markers
  report.py --compare results/baseline.json run.jsonl    per-task comparison; exit 1 on pass-rate drop/violation
"""
import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

START, END = "<!-- results:start -->", "<!-- results:end -->"
KINDS = ["float_money", "policy_outside_registry", "submitted_write"]


def load(paths):
    rows = []
    for p in paths:
        p = Path(p)
        if p.suffix == ".json":
            rows += json.loads(p.read_text())
        else:
            rows += [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    return rows


def avg(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) if xs else None


def fmt(x, nd=1):
    return "n/a" if x is None else f"{x:.{nd}f}"


def table(rows):
    by = defaultdict(list)
    for r in rows:
        by[r["mode"]].append(r)
    lines = ["| Mode | Runs | Pass rate | Tool calls before first edit | Tokens (in+out) | Time (s) | Runs with a rule violation | float money | policy outside registry | submitted write |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for mode in ("no-context", "with-context"):
        rs = by.get(mode, [])
        if not rs:
            continue
        toks = [sum(r.get("tokens", {}).get(k, 0) for k in ("input_tokens", "output_tokens")) or None for r in rs]
        vk = {k: sum(any(v["kind"] == k for v in r["violations"]) for r in rs) for k in KINDS}
        anyv = sum(any(v["kind"] in KINDS for v in r["violations"]) for r in rs)
        lines.append(f"| {mode} | {len(rs)} | {sum(r['passed'] for r in rs)}/{len(rs)} ({100 * sum(r['passed'] for r in rs) / len(rs):.0f}%) | "
                     f"{fmt(avg([r.get('calls_before_first_edit') for r in rs]))} | {fmt(avg(toks), 0)} | "
                     f"{fmt(avg([r.get('duration_s') for r in rs]))} | {anyv} | {vk['float_money']} | {vk['policy_outside_registry']} | {vk['submitted_write']} |")
    return "\n".join(lines)


def per_task(rows):
    by = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by[r["task"]][r["mode"]].append(r)
    lines = ["| Task | no-context pass | with-context pass | no-context violations | with-context violations |", "|---|---|---|---|---|"]
    for t in sorted(by):
        cells = []
        for key in ("pass", "viol"):
            for mode in ("no-context", "with-context"):
                rs = by[t].get(mode, [])
                if not rs:
                    cells.append("-")
                elif key == "pass":
                    cells.append(f"{sum(r['passed'] for r in rs)}/{len(rs)}")
                else:
                    cells.append(str(sum(len(r["violations"]) for r in rs)))
        lines.append(f"| `{t}` | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} |")
    return "\n".join(lines)


def compare(baseline, current):
    """Fail on a pass-rate drop per task vs baseline (with-context only) or any recorded violation."""
    def rate(rows):
        d = defaultdict(list)
        for r in rows:
            if r["mode"] == "with-context":
                d[r["task"]].append(r["passed"])
        return {t: sum(v) / len(v) for t, v in d.items()}
    b, c = rate(baseline), rate(current)
    lines = ["| Task | baseline | now | change |", "|---|---|---|---|"]
    failed = False
    for t in sorted(c):
        base = b.get(t)
        delta = None if base is None else c[t] - base
        bad = delta is not None and delta < 0
        failed |= bad
        lines.append(f"| `{t}` | {fmt(None if base is None else base * 100, 0)}% | {c[t] * 100:.0f}% | {'-' if delta is None else f'{delta * 100:+.0f}%'}{' :x:' if bad else ''} |")
    viol = [(r["task"], v["kind"]) for r in current if r["mode"] == "with-context" for v in r["violations"]]
    if viol:
        failed = True
        lines.append(f"\nRule violations recorded: {sorted(set(viol))}")
    return "\n".join(lines), failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--readme")
    ap.add_argument("--compare")
    a = ap.parse_args()
    if a.compare:
        text, failed = compare(load([a.compare]), load(a.files))
        print(text)
        return 1 if failed else 0
    rows = load(a.files)
    agents = sorted({r.get("agent", "claude") for r in rows})
    text = table(rows) + f"\n\nAgent(s): {', '.join(agents)}. Trials: {len(rows)}.\n\n" + per_task(rows)
    if a.readme:
        p = Path(a.readme)
        s = p.read_text()
        head, rest = s.split(START)
        _, tail = rest.split(END)
        p.write_text(f"{head}{START}\n{text}\n{END}{tail}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
