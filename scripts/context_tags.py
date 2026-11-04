#!/usr/bin/env python3
"""Map changed files (one per line on stdin) to a `--tasks` argument for run_evals.py.

Prints `all` when a change affects every task, `none` when no eval is affected, otherwise
`tag:a,tag:b`.
"""
import fnmatch
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def tags_for(changed: list[str]) -> set[str]:
    rules = yaml.safe_load((ROOT / "evals/context-map.yaml").read_text())["map"]
    out: set[str] = set()
    for f in changed:
        for rule in rules:
            if any(fnmatch.fnmatch(f, p) for p in rule["paths"]):
                out |= set(rule["tags"])
    return out


def main() -> int:
    tags = tags_for([ln.strip() for ln in sys.stdin if ln.strip()])
    print("all" if "*" in tags else (",".join(f"tag:{t}" for t in sorted(tags)) or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
