#!/usr/bin/env python3
"""Run eval tasks with and without agent context.

  run_evals.py --dry-run                     validate every task (setup fails grading, reference passes)
  run_evals.py --mode with-context --tasks fx-wrong-date-bug --trials 3
  run_evals.py --agent oracle                apply reference patches instead of calling an agent

Each trial runs in a throwaway copy of the repo (tracked files only, fresh git history).
`no-context` deletes AGENTS.md files, CLAUDE.md, .cursor/, .claude/, playbooks and ADRs first.
Results are appended to evals/results/<run_id>.jsonl; summarise with report.py.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
import checks  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TASKS = Path(__file__).parent / "tasks"
RESULTS = Path(__file__).parent / "results"
CONTEXT_PATHS = [".cursor", ".claude", "CLAUDE.md", "docs/decisions", "docs/playbooks"]
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def sh(cmd, cwd, env=None, timeout=900, check=False, **kw):
    r = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True,
                       env={**os.environ, **(env or {})}, timeout=timeout, **kw)
    if check and r.returncode:
        raise RuntimeError(f"{cmd}\n{r.stdout}\n{r.stderr}")
    return r


def load_task(task_id):
    d = TASKS / task_id
    t = yaml.safe_load((d / "task.yaml").read_text())
    t["dir"] = d
    return t


def all_task_ids():
    return sorted(p.name for p in TASKS.iterdir() if (p / "task.yaml").exists())


def make_sandbox(task, mode, work):
    """Copy tracked files, apply the setup patch, strip context if requested, commit a baseline."""
    sb = Path(tempfile.mkdtemp(prefix=f"{task['id']}-", dir=work))
    files = sh(["git", "ls-files", "-z"], ROOT).stdout.split("\0")
    for f in filter(None, files):
        if f.startswith("evals/work/") or not (ROOT / f).exists():
            continue
        dst = sb / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / f, dst)
    nm = ROOT / "apps/dashboard/node_modules"
    if nm.exists():
        (sb / "apps/dashboard/node_modules").symlink_to(nm)
    setup = task["dir"] / task.get("setup_patch", "setup.patch")
    sh(["git", "init", "-q"], sb, check=True)
    sh(["git", "config", "user.email", "eval@example.test"], sb)
    sh(["git", "config", "user.name", "eval"], sb)
    if setup.exists() and setup.stat().st_size:
        sh(["git", "apply", "--whitespace=nowarn", str(setup)], sb, check=True)
    if mode == "no-context":
        for f in sb.rglob("AGENTS.md"):
            if "node_modules" not in f.parts:
                f.unlink()
        for p in CONTEXT_PATHS:
            t = sb / p
            shutil.rmtree(t, ignore_errors=True) if t.is_dir() else t.unlink(missing_ok=True)
    (sb / ".gitignore").write_text((sb / ".gitignore").read_text() + "\nnode_modules/\n") if (sb / ".gitignore").exists() else None
    sh("git add -A && git commit -qm baseline", sb, check=True)
    return sb


def grade(task, sb):
    for h in task.get("hidden_tests", []):
        src, dst = task["dir"] / "hidden" / h, sb / h
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    env = {"TASK_DIR": str(task["dir"]), "REPO": str(sb)}
    r = sh(task["grade_command"], sb, env=env, timeout=task.get("timeout", 900))
    return r.returncode == 0, (r.stdout + r.stderr)[-1500:]


def diff_of(sb):
    sh("git add -A -N", sb)
    return sh(["git", "diff", "--no-color", "HEAD", "--", ".", ":(exclude)apps/dashboard/node_modules"], sb).stdout


def run_agent(task, mode, sb, args, run_id, trial):
    """Run Claude Code headlessly and return metrics parsed from stream-json."""
    prompt = task["prompt"].strip()
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--permission-mode", "acceptEdits",
           "--allowedTools", "Bash,Read,Edit,Write,MultiEdit,Glob,Grep",
           "--max-budget-usd", str(args.max_budget), "--no-session-persistence"]
    if args.model:
        cmd += ["--model", args.model]
    if mode == "no-context":
        cmd += ["--setting-sources", ""]  # no project hooks/settings either
    env = {}
    if args.telemetry:
        env = {
            "CLAUDE_CODE_ENABLE_TELEMETRY": "1", "OTEL_METRICS_EXPORTER": "otlp", "OTEL_LOGS_EXPORTER": "otlp",
            "OTEL_EXPORTER_OTLP_PROTOCOL": "http/json", "OTEL_EXPORTER_OTLP_ENDPOINT": args.telemetry,
            "OTEL_METRIC_EXPORT_INTERVAL": "5000", "OTEL_LOGS_EXPORT_INTERVAL": "2000",
            "OTEL_RESOURCE_ATTRIBUTES": f"eval.run_id={run_id},eval.task={task['id']},eval.mode={mode},"
                                        f"eval.trial={trial},eval.tags={'+'.join(task.get('tags', []))}",
        }
    t0 = time.time()
    r = sh(cmd, sb, env=env, timeout=task.get("agent_timeout", 1800))
    m = {"tool_calls": 0, "calls_before_first_edit": None, "tokens": {}, "cost_usd": None, "turns": None,
         "duration_s": round(time.time() - t0, 1), "agent_exit": r.returncode}
    for line in r.stdout.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "assistant":
            for block in ev.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    if block["name"] in EDIT_TOOLS and m["calls_before_first_edit"] is None:
                        fp = block.get("input", {}).get("file_path", "")
                        if not checks.is_test(fp) and not fp.endswith(".md"):
                            m["calls_before_first_edit"] = m["tool_calls"]
                    m["tool_calls"] += 1
        elif ev.get("type") == "result":
            u = ev.get("usage", {})
            m["tokens"] = {k: u.get(k, 0) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")}
            m["cost_usd"], m["turns"] = ev.get("total_cost_usd"), ev.get("num_turns")
    return m


def apply_reference(task, sb):
    sh(["git", "apply", "--whitespace=nowarn", str(task["dir"] / task.get("reference_patch", "reference.patch"))], sb, check=True)


def evaluate(task, sb):
    passed, log = grade(task, sb)
    d = diff_of(sb)
    v = checks.scan(d, task.get("forbidden_paths"), task.get("max_files"))
    return passed, log, [x.as_dict() for x in v], checks.changed_files(d)


def dry_run(ids, work):
    bad = 0
    print(f"{'task':36} {'setup fails':12} {'reference passes':17} {'violations':10} files")
    for tid in ids:
        task = load_task(tid)
        sb = make_sandbox(task, "with-context", work)
        pre, _ = grade(task, sb)
        shutil.rmtree(sb / "apps/dashboard/node_modules", ignore_errors=True) if False else None
        apply_reference(task, sb)
        post, log, viol, files = evaluate(task, sb)
        ok = (not pre) and post and not viol and len(files) <= task.get("max_files", 99)
        bad += not ok
        print(f"{tid:36} {'yes' if not pre else 'NO':12} {'yes' if post else 'NO':17} {len(viol):<10} {len(files)}  {'' if ok else '<-- FAIL'}")
        if not ok:
            print(log, viol)
    print("dry run:", "FAILED" if bad else "all tasks valid")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["with-context", "no-context", "both"], default="both")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tasks", help="comma separated ids or tags (tag:policy)")
    ap.add_argument("--trials", type=int)
    ap.add_argument("--agent", choices=["claude", "oracle"], default="claude")
    ap.add_argument("--model")
    ap.add_argument("--max-budget", type=float, default=3.0)
    ap.add_argument("--telemetry", help="OTLP/HTTP endpoint, e.g. http://localhost:4318")
    ap.add_argument("--out", default=str(RESULTS))
    args = ap.parse_args()

    ids = all_task_ids()
    if args.tasks:
        want = args.tasks.split(",")
        ids = [t for t in ids if t in want or any(w.startswith("tag:") and w[4:] in load_task(t).get("tags", []) for w in want)]
    if not ids:
        sys.exit("no matching tasks")
    work = Path(tempfile.mkdtemp(prefix="evals-"))
    try:
        if args.dry_run:
            return dry_run(ids, work)
        if args.agent == "claude" and not (os.environ.get("ANTHROPIC_API_KEY") or shutil.which("claude")):
            sys.exit("claude CLI / ANTHROPIC_API_KEY not available; use --dry-run or --agent oracle")
        run_id = time.strftime("%Y%m%d-%H%M%S")
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        modes = ["with-context", "no-context"] if args.mode == "both" else [args.mode]
        with open(out / f"{run_id}-{args.agent}.jsonl", "a") as f:
            for tid in ids:
                task = load_task(tid)
                for mode in modes:
                    for trial in range(args.trials or task.get("trials", 1)):
                        sb = make_sandbox(task, mode, work)
                        if args.agent == "oracle":
                            apply_reference(task, sb)
                            m = {"tool_calls": 0, "calls_before_first_edit": 0, "tokens": {}, "cost_usd": 0, "turns": 0, "duration_s": 0}
                        else:
                            m = run_agent(task, mode, sb, args, run_id, trial)
                        passed, log, viol, files = evaluate(task, sb)
                        rec = {"run_id": run_id, "agent": args.agent, "task": tid, "mode": mode, "trial": trial,
                               "tags": task.get("tags", []), "passed": passed, "violations": viol,
                               "files_changed": len(files), **m}
                        f.write(json.dumps(rec) + "\n")
                        f.flush()
                        print(f"{tid:36} {mode:13} trial {trial} pass={passed} violations={[v['kind'] for v in viol]}")
        print("results:", out / f"{run_id}-{args.agent}.jsonl")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
