---
name: add-report-or-export
description: Add a report or CSV export end to end (server aggregation, contract, client method, CSV with golden file).
---

# Add a report or export

1. **Server aggregation** in the policy service, in the base currency (USD) only, using integer minor units (`report` in `services/policy/api/server.go` is the model). Add a Go test.
2. **Contract**: add or extend a schema in `packages/contracts/schemas/`, run `make contracts`. Never edit generated files.
3. **Client method** on `TallyClient` in `apps/dashboard/src/api.ts`, with a test using a mocked fetch.
4. **CSV** in `apps/dashboard/src/csv.ts`, following `docs/report-format.md` exactly: fixed header order, RFC 4180 quoting, CRLF, no BOM, ISO dates, amounts with the currency's own minor digits (`formatAmount`), formula-injection prefix via `csvCell`. Document the new column list and row order in `docs/report-format.md` first.
5. **Golden file**: add `apps/dashboard/test/golden/<name>.csv` and a byte-for-byte test (see `apps/dashboard/test/csv.test.ts`). Include a JPY row, a KWD row, a cell with a comma and quote, and a cell starting with `=`.
6. **Verify**: `make test` and `make lint`.
