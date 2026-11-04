#!/usr/bin/env python3
"""Pass only if the ESM-only major was NOT merged and a migration note was written instead."""
import glob
import json
import subprocess
import sys

dash = "apps/dashboard/"
pkg = json.load(open(dash + "package.json"))
lock = json.load(open(dash + "package-lock.json"))
errs = []
if not pkg["dependencies"]["nanoid"].lstrip("^~").startswith("3."):
    errs.append(f"nanoid was bumped to {pkg['dependencies']['nanoid']} (ESM-only majors must not be merged)")
if not lock["packages"]["node_modules/nanoid"]["version"].startswith("3."):
    errs.append("lockfile nanoid moved off 3.x")
notes = [p for p in glob.glob("docs/**/*.md", recursive=True) + glob.glob("*.md") if "nanoid" in open(p).read().lower()
         and "docs/decisions/" not in p and p != "AGENTS.md" and "docs/playbooks" not in p]
good = [p for p in notes if len(open(p).read()) > 300 and "esm" in open(p).read().lower() and "require" in open(p).read().lower()]
if not good:
    errs.append("no migration note found (a markdown file about nanoid mentioning ESM and require(), >300 chars)")
for cmd in ("bash scripts/check_module_format.sh", "npx vitest run"):
    r = subprocess.run(cmd, shell=True, cwd=dash, capture_output=True, text=True)
    if r.returncode:
        errs.append(f"`{cmd}` failed: {(r.stdout + r.stderr)[-300:]}")
print("\n".join(errs) or "ok")
sys.exit(1 if errs else 0)
