# Writing agent-ready tickets

A ticket an agent can finish without guessing:

- **Outcome**: what behavior changes, in one or two sentences, with a concrete example (inputs and expected result).
- **Where**: the service or file area; name known landmines ("do not touch `legacy/`").
- **Rules that apply**: money in minor units, policy in YAML, immutability. Link `AGENTS.md` sections rather than restating them.
- **Boundaries**: the exact edge cases ("exactly at the cap" and "one cent over").
- **Verification**: which command proves it (`make test-policy`), and which fixture or golden file.
- **Out of scope**: what not to do.

Be suspicious of tickets that prescribe a mechanism ("add an edit endpoint"); state the need ("users must be able to fix a typo after submit") and let the rules shape the design.
