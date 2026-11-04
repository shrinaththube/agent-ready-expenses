# Maintaining agent context

Context is code: it has owners, review, and tests.

- Keep root `AGENTS.md` under ~80 lines. Put service detail in the nearest `AGENTS.md`. `CLAUDE.md` and `.cursor/rules/project.mdc` only point at it.
- Every path and command in a context file must exist. `python3 scripts/context_lint.py` checks this and runs in CI (`context-lint.yml`).
- Change an instruction file or skill? CI maps the changed path to eval tags and reruns those evals (`context-evals.yml`) with and without the change; a pass-rate drop or a recorded rule violation fails the PR.
- When an agent repeats a mistake: write the rule where it would have been read, then add an eval task that reproduces the mistake.
- Prefer rules that name the file and the command over adjectives.
- Delete rules that tests or hooks now enforce.
