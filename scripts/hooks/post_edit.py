#!/usr/bin/env python3
"""PostToolUse (Edit|Write|MultiEdit): format and lint the edited file; run policy tests for policy edits.
Exit 2 feeds the failure back to the agent so it fixes it in the same session."""
import json
import os
import subprocess
import sys

root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
path = json.load(sys.stdin).get("tool_input", {}).get("file_path", "")
rel = os.path.relpath(path, root) if path else ""


def run(cmd, cwd):
    try:
        r = subprocess.run(cmd, cwd=os.path.join(root, cwd), capture_output=True, text=True, timeout=120)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return 0, str(e)  # missing tool must not block the session
    return r.returncode, (r.stdout + r.stderr).strip()


problems = []
if rel.endswith(".go") and "_gen." not in rel:
    run(["gofmt", "-w", path], ".")
if rel.endswith(".py") and "_gen." not in rel and "legacy/" not in rel:
    run(["ruff", "format", path], "services/receipts")
    code, out = run(["ruff", "check", path], "services/receipts")
    if code:
        problems.append(out)
if rel.startswith(("services/policy/policy", "services/policy/policies", "fixtures/policy")):
    code, out = run(["go", "test", "./policy/..."], "services/policy")
    if code:
        problems.append("policy tests failed:\n" + out[-1500:])
if problems:
    print("\n\n".join(problems), file=sys.stderr)
    sys.exit(2)
