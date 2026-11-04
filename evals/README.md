# Evals

Does the agent context change what a coding agent does in this repo? Each task runs twice: **with-context** (the repo as is) and **no-context** (all `AGENTS.md` files, `CLAUDE.md`, `.cursor/`, `.claude/`, `docs/decisions/` and `docs/playbooks/` removed, project hooks and settings disabled). Same prompt, same hidden tests.

## Task layout (`tasks/<id>/`)

| File | Purpose |
|---|---|
| `task.yaml` | `prompt`, `tags`, `setup_patch`, `reference_patch`, `hidden_tests`, `grade_command`, `forbidden_paths`, `max_files`, `trials` |
| `setup.patch` | Introduces the bug (absent for feature tasks) |
| `reference.patch` | A known-good solution; proves the task is solvable and the grader passes it |
| `hidden/` | Hidden tests, mirrored by repo path, copied in only after the agent finishes |
| `grade.py` | Used by the dependency tasks (`$TASK_DIR` is set for `grade_command`) |

## Grading: pass/fail plus rule violations

`pass` is the hidden tests. `checks.py` separately scans the **added lines** of the agent's diff, so a correct-looking pass that broke a Tally rule is still recorded:

- `float_money`: float types, `parseFloat`, `toFixed` near money identifiers
- `policy_outside_registry`: amount/category/region comparisons in handlers or the dashboard
- `submitted_write`: assigning fields of a stored expense, or setting `Status` outside `workflow`/`store`
- `forbidden_path` (for example `legacy/`, generated files) and `too_many_files`

These are heuristics with unit tests (`tests/test_checks.py`), not proofs; the hidden tests are the authority on behavior.

## Tasks

| Id | What it tests |
|---|---|
| `add-rule-per-diem-international` | Policy as data: YAML plus a small rule-type change, boundary tests |
| `fx-wrong-date-bug` | FX uses the expense-date rate |
| `jpy-rounding-bug` | Per-currency minor digits in display and CSV |
| `csv-export-feature` | Follow `docs/report-format.md`; golden file; formula injection |
| `self-approval-bug` | Authorization plus audit |
| `edit-submitted-expense` | The literal ask (mutate) is wrong; revisions are right |
| `avoid-legacy-fx` | The ticket points at `legacy/fx_v1.py`; the bug is in `app/fx.py` |
| `receipt-parse-currency-symbol` | Parsing symbols, ISO codes, decimal commas, confidence |
| `upgrade-minor-dep` | Safe patch bump, lockfile, module check |
| `upgrade-major-dep-esm-only` | Success is not merging; write migration notes |

## Running

```bash
python3 evals/run_evals.py --dry-run                      # every task: setup fails, reference passes, no violations
python3 evals/run_evals.py --agent oracle                 # apply reference patches (pipeline check, not agent data)
python3 evals/run_evals.py --tasks tag:policy --trials 3  # real runs: needs the claude CLI and an API key
python3 evals/report.py evals/results/*.jsonl             # markdown table
```

Metrics per run: pass, violations, tool calls before the first non-test edit, tokens, time, cost. Pass `--telemetry http://localhost:4318` to tag Claude Code's OpenTelemetry export with `eval.*` resource attributes (see `docs/telemetry.md`).
