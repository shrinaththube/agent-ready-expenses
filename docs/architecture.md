# Architecture

```
dashboard (React/Vite) --/api/policy--> policy service (Go) : expenses, workflow, policy engine, audit, reports
        \--/api/receipts--> receipts service (Python/FastAPI) : receipt parsing, FX conversion
packages/contracts (JSON Schema) --make contracts--> Go structs, pydantic models, TypeScript types
fixtures/ : receipts, FX rate files, policy decision cases (no network in tests)
```

## Data flow for one expense

1. Dashboard sends receipt text to `receipts /receipts/parse` and shows the parse (asks for confirmation below 0.6 confidence).
2. If the currency is not USD, dashboard calls `receipts /fx/convert` with the **expense date** to get the base amount.
3. `policy POST /expenses` stores a draft; `POST /expenses/{id}/submit` runs draft -> submitted, evaluates `policies.yaml`, and moves to the outcome status. Both transitions are audited.
4. A manager or finance user approves or rejects from the queue; finance reimburses.
5. `GET /reports` aggregates approved spend in USD; the dashboard exports CSV client-side.

## Why these seams

- Contracts are generated so three languages cannot drift on money shape.
- Policy decisions are pure functions of (expense, same-day context, policies.yaml), which makes them table-testable.
- The store exposes only `Create` and `Transition`; there is no edit path for a submitted expense.
- The store is in-memory: the interface is small enough to swap for SQLite or Postgres, but persistence is not what this repo demonstrates.

## Demo authentication

Actor identity comes from `X-Actor-ID` / `X-Actor-Role` headers. This is a stand-in; a real deployment verifies a token and derives both.
