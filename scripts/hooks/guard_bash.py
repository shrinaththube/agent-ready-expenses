#!/usr/bin/env python3
"""PreToolUse (Bash): block dangerous shell commands. Exit 2 = block."""
import json
import re
import sys

DANGEROUS = [
    (r"\brm\s+-[a-z]*[rf][a-z]*\s+(-[a-z]+\s+)*(/|~|\$HOME|\.\.?)(\s|$)", "recursive delete of a root, home or parent path"),
    (r"\bgit\s+push\b.*(--force|\s-f\b)", "force push"),
    (r"\bgit\s+reset\s+--hard\b", "hard reset discards work"),
    (r"(curl|wget)[^|]*\|\s*(ba|z)?sh\b", "piping a download into a shell"),
    (r"\bchmod\s+-R\s+777\b", "world-writable permissions"),
    (r"\bDROP\s+(TABLE|DATABASE)\b", "destructive SQL"),
]
cmd = json.load(sys.stdin).get("tool_input", {}).get("command", "")
for rx, why in DANGEROUS:
    if re.search(rx, cmd, re.I):
        print(f"Blocked command ({why}): {cmd}", file=sys.stderr)
        sys.exit(2)
