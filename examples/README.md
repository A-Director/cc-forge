# Examples

> These are **real session captures**, not synthesized examples.

Every file in this directory is a verbatim snapshot from an actual
cc-forge project session. Names of people, projects, and infra may
be lightly redacted, but the structure, the Hermes output, the gate
findings, and the decision trails are real.

The point: when you're trying to figure out what cc-forge actually
looks like in use — not what the README claims, but what shows up
on screen — these files are the answer.

## Folders

- **`session-closures/`** — End-of-session Hermes summaries. Useful
  for seeing the closing-banner pattern in real use, with real
  task IDs, real backlog deltas, real "next session" pointers.

More capture categories (gate reviews, status snapshots, phase
transitions) will be added here as real sessions produce them.

## Contributing a capture

Add a new file with the date prefix and a short slug:
`YYYY-MM-DD-<project>-<what>.md`. Example:
`2026-05-21-clark-phase-1.5-closure.md`.

Strip secrets, customer names, and PII before committing. Leave the
Hermes output structure intact — that's the whole point.
