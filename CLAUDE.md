@AGENTS.md

## Claude Code specifics

- Use plan mode for changes to the workflow (`services/policy/workflow/`) or to policies.
- Skills in `.claude/skills/`, the `reviewer` subagent in `.claude/agents/reviewer.md`, and slash commands `/plan`, `/review`, `/done-check`, `/policy-check` in `.claude/commands/`.
- Hooks in `.claude/settings.json` block edits to generated files and `legacy/`, and run formatters and policy tests after edits.
