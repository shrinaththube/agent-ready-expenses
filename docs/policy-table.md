# Policy table

Source of truth: `services/policy/policies/policies.yaml`. This table is documentation and is checked by a test: every policy id must appear here in backticks. Amounts are base currency (USD). Rules run in order; the most restrictive outcome wins (`auto_approved` < `pending_manager` < `pending_finance` < `rejected`). An expense that matches nothing is auto-approved.

| Policy id | Rule type | Applies to | Condition | Outcome |
|---|---|---|---|---|
| `meals-per-diem` | `per_person_daily_cap` | meals | (same-day prior spend + amount) > $75.00 × attendees | `pending_manager` |
| `manager-over-200` | `amount_threshold` | all | amount > $200.00 | `pending_manager` |
| `finance-at-1000` | `amount_threshold` | all | amount ≥ $1,000.00 | `pending_finance` |
| `travel-needs-receipt` | `requires_receipt` | travel | no receipt | `rejected` |
| `alcohol-needs-manager` | `category_match` | alcohol | always | `pending_manager` |
| `weekend-software-flag` | `weekend` | software | dated Saturday or Sunday | `pending_manager` |

Boundary cases (exactly at the limit, one cent over) are in `fixtures/policy/cases.json` and run by `TestPolicyTable`.
