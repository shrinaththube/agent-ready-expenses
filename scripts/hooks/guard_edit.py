#!/usr/bin/env python3
"""PreToolUse (Edit|Write|MultiEdit): block generated files and legacy code. Exit 2 = block."""
import json
import re
import sys

BLOCKED = [
    (re.compile(r"(_gen\.(go|py)|\.gen\.ts)$"), "generated file: edit packages/contracts/schemas and run `make contracts`"),
    (re.compile(r"(^|/)legacy/"), "legacy code is deprecated: fix the current module (services/receipts/app/) instead"),
]
path = json.load(sys.stdin).get("tool_input", {}).get("file_path", "")
for rx, why in BLOCKED:
    if rx.search(path):
        print(f"Blocked edit to {path}: {why}", file=sys.stderr)
        sys.exit(2)
