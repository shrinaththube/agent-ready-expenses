# 0004: nanoid is pinned to 3.x for CommonJS compatibility

Status: accepted

`apps/dashboard/scripts/seed-demo.cjs` and other Node tooling load dependencies with `require()`. `nanoid` 4 and later are ESM-only, so `require('nanoid')` throws `ERR_REQUIRE_ESM`. We pin `nanoid` to `3.3.x` (exact version in `package.json`) and run `apps/dashboard/scripts/check_module_format.sh` in CI and before any dependency change.

Revisit when the scripts move to ESM. Until then a major bump is not a drop-in upgrade: write migration notes (see `docs/upgrades/`) instead of merging it.
