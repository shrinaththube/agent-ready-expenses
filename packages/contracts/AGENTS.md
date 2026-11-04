# packages/contracts

JSON Schema is the single source of truth for cross-service types.

- Edit `schemas/*.schema.json`, then run `make contracts` from the repo root.
- Generated files (`contracts_gen.go`, `contracts_gen.py`, `contracts.gen.ts`) are never edited by hand; CI fails on a dirty diff after `make contracts`.
- `generate.py` rejects `number` on money-like property names. Money is always the `Money` schema (integer `amount_minor` + `currency`).
- Enums are their own schema files so every language shares one type.
