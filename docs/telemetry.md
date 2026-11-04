# Telemetry

Claude Code can export OpenTelemetry metrics and log events. This repo collects them locally and turns them into agent-behavior metrics. Variable names below were checked against the Claude Code monitoring docs.

## Setup

```bash
cd observability
docker compose up -d                  # collector on :4317 (gRPC) / :4318 (HTTP), viewer on :8088
source claude-env.sh                  # CLAUDE_CODE_ENABLE_TELEMETRY=1, OTLP exporters, http/json, localhost:4318
claude                                # any session now exports
```

No Docker? `python3 observability/mini_collector.py` is a stdlib OTLP/HTTP JSON receiver that writes the same file.

Eval runs tag their sessions: `python3 evals/run_evals.py --telemetry http://localhost:4318 ...` sets `OTEL_RESOURCE_ATTRIBUTES` with `eval.run_id`, `eval.task`, `eval.mode`, `eval.trial` and `eval.tags`, so every metric and event carries them.

## What is exported (used here)

| Signal | Name | Used for |
|---|---|---|
| log event | `claude_code.tool_result` (`tool_name`, `success`, `duration_ms`) | orientation cost, loops |
| log event | `claude_code.api_request` (`input_tokens`, `output_tokens`, `cost_usd`, `duration_ms`) | tokens, cost |
| metric | `claude_code.token.usage` (`type`: input/output/cacheRead/cacheCreation) | token fallback |
| metric | `claude_code.cost.usage`, `claude_code.session.count` | spot checks |

Prompt text and tool arguments are off by default (`OTEL_LOG_USER_PROMPTS`, `OTEL_LOG_TOOL_DETAILS`); `claude-env.sh` enables tool details only.

## Derived metrics (`observability/viewer.py`)

- **Orientation cost**: tool calls before the first Edit/Write. High means the agent is hunting for where to work.
- **Loops**: failed tool calls (retries, failing test commands).
- **Success by tag** and **tokens per success**: join sessions to `evals/results/*.jsonl` by `eval.*` attributes.

```bash
python3 observability/viewer.py observability/data/telemetry.jsonl --results evals/results/<run>.jsonl
python3 observability/viewer.py observability/data/telemetry.jsonl --serve 8088   # HTML view (also what compose runs)
```

## Verification status

The collector-to-viewer path is tested with OTLP JSON payloads shaped like the documented events (`observability/tests/test_telemetry.py`). A live Claude Code session needs an API key; with one, run the setup above and the session appears in the viewer keyed by `session.id`.
