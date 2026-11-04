---
name: add-currency
description: Add support for a new currency (FX rates, minor-digit count, display and conversion tests).
---

# Add a currency

1. **Minor digits**: look up the ISO 4217 exponent (JPY 0, USD 2, KWD 3, ...). Add it to all three tables, which must agree: `services/receipts/app/money.py`, `services/policy/money/money.go`, `apps/dashboard/src/money.ts`.
2. **Rates**: add the code to every `fixtures/fx/rates-2024-03-15.json`-style file in `fixtures/fx/` (units of the currency per 1 USD, decimal strings, never numbers).
3. **Tests**:
   - Python `services/receipts/tests/test_fx.py`: conversion to and from USD at an expense-date rate, including one case where the currency's digits differ from USD's.
   - Round trip, minor -> decimal string -> minor, in `services/receipts/tests/test_fx.py` and `apps/dashboard/test/money.test.ts`.
   - Go display case in `services/policy/money/money_test.go`.
4. **Rules**: money stays integer minor units; FX math in `Decimal`; half-even rounding once at the end; use the rate on the expense date.
5. **Verify**: `make test` and `make lint`.
