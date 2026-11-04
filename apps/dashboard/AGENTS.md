# apps/dashboard (TypeScript, Vite + React, Vitest)

- Money is `{amount_minor: integer, currency}`. Format and parse only through `src/money.ts` (uses `minorDigits`); never `parseFloat`, `toFixed` or `Number` on amounts.
- CSV lives in `src/csv.ts` and must follow `docs/report-format.md` (RFC 4180, CRLF, no BOM, formula-injection prefix, currency's own minor digits). Every export has a golden file in `test/golden/`.
- `src/contracts.gen.ts` is generated; change `packages/contracts` and run `make contracts`.
- API calls go through `src/api.ts` (`TallyClient`); components never call `fetch` directly.
- Low-confidence receipt parses (`needsConfirmation`) must be confirmed by the user before submit.
- `nanoid` is pinned to 3.x because `scripts/seed-demo.cjs` uses `require()`. Run `bash scripts/check_module_format.sh` before and after dependency changes; see `docs/decisions/0004-pin-nanoid-commonjs.md`.
- Tests: `cd apps/dashboard && npx vitest run`; types: `npx tsc --noEmit`.
