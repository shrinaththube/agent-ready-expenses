# Tally: product spec

Tally handles team expenses. Employees submit expenses with receipts; a policy engine routes each one (auto-approve, manager, finance, reject); a worker parses receipts and converts currencies; managers and finance get queues, reports and CSV export.

## Expense lifecycle

`draft -> submitted -> (auto_approved | pending_manager | pending_finance | rejected)`, then `pending_* -> approved | rejected`, then `approved | auto_approved -> reimbursed`.

- Legal transitions live in `services/policy/workflow/transitions.go`.
- A submitted expense is immutable. A correction is a new revision (`revision` + `revision_of`), never an edit.
- Every transition appends an audit entry (actor, from, to, reason, timestamp). The log has no update or delete.
- An actor may not approve or reject their own expense. Manager queue needs the `manager` role, finance queue the `finance` role.

## Policy engine

Policies are data in `services/policy/policies/policies.yaml`, evaluated in order; the most restrictive outcome wins. Each rule type is a Go type registered in `services/policy/policy/rules/registry.go`. A decision lists the matched rules and a readable reason. The current table is in `docs/policy-table.md`. Policies evaluate in the base currency (USD) after conversion.

## Money and FX

- Money is integer minor units plus an ISO currency code. No floats anywhere (Go `int64`, Python `Decimal` for FX math, TypeScript integers).
- FX uses the rate in `fixtures/fx/rates-YYYY-MM-DD.json` for the **expense date** (weekends fall back to the previous file, within 7 days), half-even rounding applied once at the end. JPY has 0 minor digits, KWD has 3.

## Receipts

Rule-based parsing (regex plus heuristics) of text or simple PDF receipts into merchant, date, total and currency, with a confidence score. Below 0.6 the dashboard asks the user to confirm.

## Reports and export

Totals by employee, category and month in USD for approved spend, plus counts by status. CSV format: `docs/report-format.md`.
