# Migrations

Forward-only migration scripts for `state.json` schema changes (and other
project-state shapes) per spec §3.9.

## Naming

`<from-version>-to-<to-version>-<short-description>.sh` — for example
`1.0.0-to-1.1.0-add-operator-actions.sh`. Scripts are idempotent: re-running
on an already-migrated state is a no-op.

## Invocation

`/hermes-update` (post-Session-0) reads the project's `state.json`
`schema_version` field and runs any migrations whose `<from-version>` matches.
Migrations apply in semver order.

## v1.0.0 baseline

No migrations ship with v1.0.0. The first migration will land when the
state.json schema first changes (e.g., adding a new required field).
