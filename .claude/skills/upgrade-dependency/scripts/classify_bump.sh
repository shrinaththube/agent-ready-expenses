#!/usr/bin/env bash
# Usage: classify_bump.sh <current> <target>  ->  prints patch | minor | major | none
set -euo pipefail
IFS=. read -r a1 a2 a3 <<<"${1#v}"
IFS=. read -r b1 b2 b3 <<<"${2#v}"
if [ "$a1" != "$b1" ]; then echo major
elif [ "$a2" != "$b2" ]; then echo minor
elif [ "${a3%%-*}" != "${b3%%-*}" ]; then echo patch
else echo none; fi
