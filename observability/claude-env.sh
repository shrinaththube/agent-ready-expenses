# source this, then run `claude` (or run_evals.py --telemetry http://localhost:4318)
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=http/json
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export OTEL_METRIC_EXPORT_INTERVAL=10000
export OTEL_LOGS_EXPORT_INTERVAL=2000
export OTEL_LOG_TOOL_DETAILS=1
# Eval runs add eval.* resource attributes automatically; for a manual session you can set them yourself:
export OTEL_RESOURCE_ATTRIBUTES="${OTEL_RESOURCE_ATTRIBUTES:-eval.task=manual,eval.mode=with-context,eval.trial=0,eval.run_id=manual}"
