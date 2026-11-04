#!/usr/bin/env python3
"""Check that every path and `make` target mentioned in agent context files exists."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GLOBS = [
    "AGENTS.md", "CLAUDE.md", "*/*/AGENTS.md", "*/AGENTS.md", ".cursor/rules/*.mdc",
    ".claude/skills/*/SKILL.md", ".claude/agents/*.md", ".claude/commands/*.md", "docs/playbooks/*.md",
]
TICK = re.compile(r"`([^`\n]+)`")
PATHLIKE = re.compile(r"^[\w.@/-]+$")
EXT = (".md", ".go", ".py", ".ts", ".tsx", ".yaml", ".yml", ".json", ".sh", ".cjs", ".mdc", ".csv")


def make_targets() -> set[str]:
    text = (ROOT / "Makefile").read_text()
    return set(re.findall(r"^([A-Za-z0-9_.-]+):", text, re.M))


def candidates(path: Path, token: str):
    yield ROOT / token
    yield path.parent / token
    # Bare names ("policies.yaml", "legacy/") may refer to a file or directory anywhere in the repo.
    name = token.rstrip("/")
    if "/" not in name:
        yield from (p for p in ROOT.rglob(name) if "node_modules" not in p.parts and ".git" not in p.parts)


def check(path: Path, targets: set[str]) -> list[str]:
    errs = []
    for m in TICK.finditer(path.read_text()):
        tok = m.group(1).strip()
        if mk := re.match(r"^make ([\w-]+)$", tok):
            if mk[1] not in targets:
                errs.append(f"{path.relative_to(ROOT)}: make target `{mk[1]}` not in Makefile")
            continue
        if re.match(r"^/[\w-]+$", tok):  # slash command
            if not (ROOT / ".claude/commands" / f"{tok[1:]}.md").exists():
                errs.append(f"{path.relative_to(ROOT)}: command `{tok}` has no .claude/commands file")
            continue
        for part in re.split(r"\s+", tok):
            part = part.rstrip(".,:;)")
            if not PATHLIKE.match(part) or part.startswith(("-", "http", "./")) or "*" in part:
                continue
            if "/" not in part and not part.endswith(EXT):
                continue
            if part.startswith(".") and "/" not in part:
                continue
            if part in {"net/http", "go.mod"} or part.startswith(("X-", "node:")):
                continue
            if not any(c.exists() for c in candidates(path, part)):
                if _generated_or_runtime(part):
                    continue
                errs.append(f"{path.relative_to(ROOT)}: path `{part}` does not exist")
    return errs


def _generated_or_runtime(part: str) -> bool:
    # Names that are patterns or created at runtime, not repo paths.
    return part.startswith(("mock/", "evals/work/", "tally/")) or "YYYY" in part or part in {
        "application/json", "text/csv", "md/json"}


def main() -> int:
    targets = make_targets()
    files = sorted({p for g in GLOBS for p in ROOT.glob(g) if p.is_file()})
    errs = [e for f in files for e in check(f, targets)]
    for e in errs:
        print("ERROR", e)
    print(f"context-lint: {len(files)} files checked, {len(errs)} problems")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
