---
name: upgrade-dependency
description: Upgrade a dependency safely (patch/minor directly, major as a draft with migration notes) and analyse security advisories.
---

# Upgrade a dependency

1. **Classify** the bump with `bash .claude/skills/upgrade-dependency/scripts/classify_bump.sh <current> <target>`; it prints `patch`, `minor`, `major` or `none`.
2. **Baseline**: run `bash apps/dashboard/scripts/check_module_format.sh` and `make test` before changing anything.
3. **Patch or minor**: update the exact version in the manifest and lockfile, run `make test`, `make lint`, and `bash apps/dashboard/scripts/check_module_format.sh`. Commit directly.
4. **Major**: do not merge it. Try it only on a scratch branch to learn what breaks, then revert and write migration notes in `docs/upgrades/<package>-<version>.md`: what changed, what breaks here (for example ESM-only packages versus our `require()` scripts and `docs/decisions/0004-pin-nanoid-commonjs.md`), the migration steps, and the risk. Open it as a draft PR with those notes.
5. **Always** run `check_module_format.sh`; pinned packages must still load with `require()`.
6. **Security advisories**: if the vulnerable code path is not reachable from this repo, write a short "not affected" analysis (advisory id, affected function, why we do not call it) in the PR instead of forcing an upgrade.
