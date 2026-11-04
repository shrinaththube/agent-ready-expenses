.PHONY: test lint contracts evals e2e test-policy test-receipts test-dashboard

test: test-policy test-receipts test-dashboard

test-policy:
	cd services/policy && go test ./...

test-receipts:
	cd services/receipts && python3 -m pytest -q

test-dashboard:
	cd apps/dashboard && npx vitest run

lint:
	cd services/policy && gofmt -l . | (! grep .) && go vet ./...
	cd services/receipts && ruff check . && ruff format --check .
	cd apps/dashboard && npx tsc --noEmit

contracts:
	python3 packages/contracts/generate.py

e2e:
	python3 scripts/e2e.py

evals:
	python3 evals/run_evals.py --dry-run
