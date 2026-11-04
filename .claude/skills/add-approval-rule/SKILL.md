---
name: add-approval-rule
description: Add or change an expense approval policy (cap, threshold, category, receipt, weekend or region rule). Use whenever a task changes who must approve an expense or when it is rejected.
---

# Add an approval rule

Policies are data (`docs/decisions/0002-policies-as-data.md`). Never put approval logic in `services/policy/api/`.

1. **Read** `services/policy/AGENTS.md` and `services/policy/policies/policies.yaml`.
2. **Can an existing rule type express it?** Types: `amount_threshold`, `category_match`, `requires_receipt`, `per_person_daily_cap`, `weekend` (see `services/policy/policy/rules/registry.go`).
   - Yes: add or edit YAML only.
   - No: add `services/policy/policy/rules/<type>.go` modelled on `per_person_daily_cap.go` (struct with yaml tags, validating factory, `ID`, `Evaluate`) and register it in `registry.go`. An optional field on an existing type is also fine if it keeps old YAML working.
3. **Boundary cases** in `fixtures/policy/cases.json`: exactly at the threshold, one cent over (and one under when it matters). Amounts are USD minor units, so $75.00 is `7500`.
4. **Docs**: add or update the row in `docs/policy-table.md` (a test fails if a policy id is missing).
5. **Verify**: `make test-policy`, then `/policy-check` to see the decision matrix. Remember the most restrictive outcome wins, so check interaction with `manager-over-200` and `finance-at-1000`.

Done when: YAML (and rule type if needed), cases, docs row, and tests are in one change; nothing added under `api/`.
