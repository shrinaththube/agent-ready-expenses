# services/policy (Go)

Expenses, workflow, policy engine, audit, reports. Module `tally/policy`, stdlib `net/http` (Go 1.22 mux patterns).

## Layout

- `contracts/` generated types (do not edit). `workflow/transitions.go` legal transitions; `workflow/workflow.go` `Authorize` and `Apply`.
- `policy/engine.go` loads `policies/policies.yaml` and evaluates; `policy/rules/` one file per rule type; `policy/rules/registry.go` maps the YAML `type:` to a factory.
- `store/memory.go` repository (only `Create` and `Transition`; no edit path); `audit/` append-only log; `api/server.go` HTTP handlers.

## Evaluation order

Rules run in the order they appear in `policies.yaml`. Every matching rule contributes an outcome; **the most restrictive wins**: `auto_approved` < `pending_manager` < `pending_finance` < `rejected`. No match means `auto_approved`. The decision lists every matched rule and a readable reason. Amounts are base-currency (USD) minor units.

## Adding a rule

1. Can an existing type express it? Then edit only `policies/policies.yaml`.
2. If not, add `policy/rules/<type>.go` (copy `per_person_daily_cap.go`: a struct with yaml tags, a factory that validates, `ID()`, `Evaluate()`), and register it in `policy/rules/registry.go`.
3. Add boundary cases (exactly at the limit, one cent over) to `fixtures/policy/cases.json`.
4. Add the rule to `docs/policy-table.md` (a test fails if a policy id is missing).

Handlers in `api/` translate HTTP only. Do not compare amounts, categories or regions there.

## Conventions

- Wrap errors with `%w`; no `panic`; table-driven tests.
- Money fields are `int64` minor units. No `float64` anywhere near amounts.
- Never assign to fields of a stored non-draft expense. Status changes go through `store.Transition` + `workflow.Apply`, which writes the audit entry.
- Authorization (including "no self-approval") lives in `workflow.Authorize`.
- Run `cd services/policy && go test ./...`; `go run ./cmd/policymatrix` prints the decision matrix.
