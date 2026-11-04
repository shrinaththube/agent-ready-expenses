---
description: Run policy table tests and print the decision matrix for the fixtures
---

Run `cd services/policy && go test ./policy/... && go run ./cmd/policymatrix`. Show the decision matrix. Flag any row marked "expected" (a mismatch) and explain which policy in `services/policy/policies/policies.yaml` caused it.
