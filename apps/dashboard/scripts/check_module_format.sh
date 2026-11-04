#!/usr/bin/env bash
# Verifies that dependencies pinned for CommonJS compatibility still load via require().
# See docs/decisions/0004-pin-nanoid-commonjs.md. Run before and after any dependency upgrade.
set -euo pipefail
cd "$(dirname "$0")/.."
PINNED=(nanoid)
fail=0
for dep in "${PINNED[@]}"; do
  if node -e "require('$dep')" 2>/dev/null; then
    echo "ok   $dep loads with require() ($(node -p "require('$dep/package.json').version"))"
  else
    echo "FAIL $dep is not CommonJS-compatible at the installed version" >&2
    fail=1
  fi
done
exit $fail
