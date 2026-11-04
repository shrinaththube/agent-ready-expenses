.PHONY: test lint contracts evals test-policy

test: test-policy

test-policy:
	cd services/policy && go test ./...

lint:
	cd services/policy && gofmt -l . | (! grep .) && go vet ./...

contracts:
	python3 packages/contracts/generate.py
