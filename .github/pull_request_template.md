## What and why

<!-- One or two sentences. Link the ticket. -->

## Definition of done

- [ ] `make test` and `make lint` pass
- [ ] Contracts regenerated (`make contracts`) if schemas changed; no hand-edited generated files
- [ ] `docs/policy-table.md` updated if policies changed
- [ ] Money stays integer minor units; policies stay in `policies.yaml`; submitted expenses untouched
- [ ] Context files changed? `python3 scripts/context_lint.py` passes and affected evals were considered

## Notes for reviewers
