#!/usr/bin/env python3
"""Pass if dayjs was bumped within major 1 (manifest and lockfile agree), nothing else moved,
the CommonJS check passes and tests are green."""
import json
import re
import subprocess
import sys

dash = "apps/dashboard/"
pkg = json.load(open(dash + "package.json"))
lock = json.load(open(dash + "package-lock.json"))
ver = pkg["dependencies"]["dayjs"].lstrip("^~")
tup = tuple(int(x) for x in re.match(r"(\d+)\.(\d+)\.(\d+)", ver).groups())
errs = []
if not ((1, 11, 10) < tup < (2, 0, 0)):
    errs.append(f"dayjs {ver} is not a minor/patch bump within 1.x above 1.11.10")
if lock["packages"]["node_modules/dayjs"]["version"] != ver:
    errs.append("lockfile dayjs version does not match package.json")
if not pkg["dependencies"]["nanoid"].startswith("3."):
    errs.append("nanoid must stay on 3.x")
if pkg["dependencies"]["react"] != "18.3.1":
    errs.append("unrelated dependency changed")
for cmd in ("bash scripts/check_module_format.sh", "npx vitest run"):
    r = subprocess.run(cmd, shell=True, cwd=dash, capture_output=True, text=True)
    if r.returncode:
        errs.append(f"`{cmd}` failed: {(r.stdout + r.stderr)[-300:]}")
print("\n".join(errs) or "ok")
sys.exit(1 if errs else 0)
