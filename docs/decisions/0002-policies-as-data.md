# 0002: Approval policies are data, rule types are code

Status: accepted

Policies live in `services/policy/policies/policies.yaml`. Each entry names a `type` that maps, via `policy/rules/registry.go`, to a small Go type. A new policy is usually YAML only; a genuinely new kind of condition adds one rule type and registers it. HTTP handlers never contain approval logic.

Why: finance can read and review the YAML diff, boundary behavior is table-testable (`fixtures/policy/cases.json`), and "the most restrictive outcome wins" is enforced in one place. `if amount > 1000` in a handler would be invisible to all of that.
