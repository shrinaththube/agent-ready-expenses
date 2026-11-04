---
description: Run the definition-of-done checks
---

Run the definition of done from `AGENTS.md`:

1. `make test` and `make lint`.
2. `make contracts`, then confirm `git status` shows no unexpected generated-file changes.
3. If policies changed, confirm `docs/policy-table.md` lists every policy id.
4. `python3 scripts/context_lint.py` if any context file changed.
5. Run `/review`.

Report each item as pass or fail with evidence. Do not claim done if any item fails.
