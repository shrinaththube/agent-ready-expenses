# Skill exercises

Each skill in `.claude/skills/` was exercised once; this records where.

| Skill | Exercise | Evidence |
|---|---|---|
| `add-currency` | Added BHD (3 minor digits): three digit tables, all `fixtures/fx` rate files, conversion, round-trip and display tests | `BHD` cases in `services/receipts/tests/test_fx.py`, `services/policy/money/money_test.go`, `apps/dashboard/test/money.test.ts` |
| `add-approval-rule` | Eval task `add-rule-per-diem-international` reference patch (extends `per_person_daily_cap`, YAML, boundary cases, docs row) | `evals/tasks/add-rule-per-diem-international/` |
| `add-report-or-export` | Eval task `csv-export-feature` reference patch (contract-free client CSV, golden file) | `evals/tasks/csv-export-feature/` |
| `upgrade-dependency` | Eval tasks `upgrade-minor-dep` (direct bump) and `upgrade-major-dep-esm-only` (migration note, no merge); `classify_bump.sh` | `evals/tasks/upgrade-*/`, `.claude/skills/upgrade-dependency/scripts/classify_bump.sh` |

Hooks are tested with `python3 scripts/hooks/test_hooks.py` (same stdin payloads Claude Code sends).
