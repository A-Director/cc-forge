"""
Hermes write-path validator + retry loop (Session D, Phase D).

Implements the §3.8 validate-and-retry contract: a persona-produced
structured write (backlog item, intake entry, etc.) is validated AT
WRITE TIME against the format contract, and on failure the specific
violation is fed back to the writer for self-correction before the
write is considered complete.

This is the complement to retrospective parsing: retrospective parsing
catches hand-edits and absent-input drift (read-side); validate-and-retry
catches malformed persona writes at the source (write-side). Both are
needed.

Retry classification:
  - RETRYABLE  — persona produced output that fails its format contract.
                 The persona can be re-prompted with the specific
                 violation; the next attempt should succeed.
  - NON_RETRYABLE — required input is absent (e.g., a referenced item
                    doesn't exist; a required upstream document is
                    missing). The writer cannot conjure missing
                    information. Hard-fail; surface to operator.
  - BUDGET_EXHAUSTED — persona retried up to the budget and still
                       failed. Treat as a hard format failure. Log
                       hard_format_failure and surface.

Retry budget: 3 attempts (initial + 2 retries). Configurable per write
type via the writer's call site. Three is the chosen default because:
  - One attempt is the no-retry status quo.
  - Two attempts catches one-shot mistakes (typo, wrong key).
  - Three attempts is enough for a persona to read the feedback,
    revise, and try once more. Beyond three suggests a structural
    persona-prompt problem that re-prompting won't fix.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

# Backlog-item field/status contract per §3.2 — sourced from the canonical
# module (Session F) so the write-path validator and the readers (Argus,
# dashboard, classifier) cannot disagree on what a valid item is.
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))
from _hermes_backlog import (  # noqa: E402
    REQUIRED_FIELDS as REQUIRED_BACKLOG_FIELDS,
    GRANDFATHERED_FIELD,
    VALID_STATUS_VALUES,
    VALID_PHASE_VALUES,
)

DEFAULT_RETRY_BUDGET = 3


@dataclass
class Violation:
    """A single format violation. The `field` and `message` are the
    surface fed back to the persona in retry feedback."""
    field: str
    message: str
    retryable: bool


def validate_backlog_item(item: dict[str, Any]) -> list[Violation]:
    """Validate a backlog item per §3.2. Returns list of violations.
    Retryability: field-shape errors are retryable; absent inputs are
    not."""
    violations: list[Violation] = []

    # ID
    item_id = item.get("id", "")
    if not isinstance(item_id, str) or not re.match(r"^[A-Z]{2,4}(-[A-Z]{2,4}){0,2}-\d{3}$", item_id):
        violations.append(Violation(
            field="id",
            message=f"id must match ^[A-Z]{{2,4}}(-[A-Z]{{2,4}}){{0,2}}-\\d{{3}}$; got {item_id!r}",
            retryable=True,
        ))

    fields = item.get("fields") or {}
    if not isinstance(fields, dict):
        violations.append(Violation(
            field="fields",
            message=f"fields must be an object; got {type(fields).__name__}",
            retryable=True,
        ))
        return violations  # no point checking individual fields

    # Required fields presence
    for required in REQUIRED_BACKLOG_FIELDS:
        if required not in fields or not str(fields.get(required, "")).strip():
            if required == GRANDFATHERED_FIELD:
                # Standard is grandfathered per §3.2 line 644 for one
                # transition cycle. For NEW writes, it's still required.
                # The grandfathering is a READ-side concession for
                # pre-existing items; write-side requires it.
                violations.append(Violation(
                    field=required,
                    message=f"required field '{required}' missing or empty (§3.2 — "
                            f"required for new writes; grandfathering is read-side only)",
                    retryable=True,
                ))
            else:
                violations.append(Violation(
                    field=required,
                    message=f"required field '{required}' missing or empty",
                    retryable=True,
                ))

    # Closed-vocabulary field values
    status = fields.get("Status", "")
    if status and status not in VALID_STATUS_VALUES:
        violations.append(Violation(
            field="Status",
            message=f"Status must be one of {sorted(VALID_STATUS_VALUES)}; got {status!r}",
            retryable=True,
        ))
    phase = str(fields.get("Phase", ""))
    # Phase values may be "1" or "1 (MVP)" — strip the parenthesised suffix.
    phase_num = phase.split()[0] if phase else ""
    if phase_num and phase_num not in VALID_PHASE_VALUES:
        violations.append(Violation(
            field="Phase",
            message=f"Phase must be one of {sorted(VALID_PHASE_VALUES)} (number or —); got {phase!r}",
            retryable=True,
        ))

    return violations


def feedback_for_persona(violations: list[Violation], context: str = "") -> str:
    """Format the retry feedback the persona sees. Specific and
    actionable: every violation names its field and the exact rule.
    Encodes the spec's distinction between 'this is malformed, try
    again' and 'this is missing input, can't help you'."""
    lines = [f"VALIDATION FAILED ({len(violations)} violations) — write must conform to §3.2 contract."]
    if context:
        lines.append(f"Context: {context}")
    lines.append("")
    lines.append("Violations:")
    for v in violations:
        marker = "↻" if v.retryable else "✗"
        lines.append(f"  {marker} {v.field}: {v.message}")
    lines.append("")
    has_retryable = any(v.retryable for v in violations)
    if has_retryable:
        lines.append(
            "Action: revise the write to satisfy the contract above. "
            "The contract is closed — do not invent values; if a required "
            "input genuinely doesn't exist, mark the write as "
            "non-retryable and surface to the operator."
        )
    return "\n".join(lines)


def log_format_violation(project_root: Path, file_path: str,
                         severity: str, expected: str, found: str,
                         retryable: bool, attempt: int) -> None:
    """Emit a format_violation event per §3.6."""
    usage_log = project_root / ".cc-forge" / "usage.log"
    iso_ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = {
        "ts": iso_ts,
        "type": "format_violation",
        "data": {
            "file": file_path,
            "severity": severity,  # 'strict' | 'advisory' | 'hard_failed'
            "expected": expected,
            "found": found,
            "retryable": retryable,
            "attempt": attempt,
        },
    }
    try:
        usage_log.parent.mkdir(parents=True, exist_ok=True)
        with usage_log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError:
        pass


@dataclass
class RetryResult:
    success: bool
    attempts: int
    final_violations: list[Violation]
    hard_failure: bool = False
    reason: str = ""


def run_validate_retry(
    *,
    writer: Callable[[int, list[Violation] | None], dict[str, Any]],
    validator: Callable[[dict[str, Any]], list[Violation]],
    project_root: Path,
    write_target_file: str,
    budget: int = DEFAULT_RETRY_BUDGET,
) -> RetryResult:
    """
    Run the validate-and-retry loop with a known budget.

    writer(attempt, prev_violations) → dict (the proposed write)
    validator(write) → list[Violation]  (empty on success)

    Logs format_violation events as the loop progresses; on
    BUDGET_EXHAUSTED logs a hard_format_failure event so the operator
    can see the trail. On the first non-retryable violation, stops and
    reports non-retryable.
    """
    prev_violations: list[Violation] | None = None
    last_write: dict[str, Any] | None = None
    for attempt in range(1, budget + 1):
        write = writer(attempt, prev_violations)
        last_write = write
        violations = validator(write)

        if not violations:
            return RetryResult(success=True, attempts=attempt, final_violations=[])

        # Any non-retryable violation halts the loop immediately —
        # there's no point asking a persona for what isn't available.
        non_retryable = [v for v in violations if not v.retryable]
        if non_retryable:
            for v in non_retryable:
                log_format_violation(
                    project_root,
                    file_path=write_target_file,
                    severity="strict",
                    expected=v.field,
                    found=v.message,
                    retryable=False,
                    attempt=attempt,
                )
            return RetryResult(
                success=False, attempts=attempt,
                final_violations=violations,
                hard_failure=False,
                reason="non_retryable_input_missing",
            )

        # Retryable — log and loop (unless we're out of budget).
        for v in violations:
            log_format_violation(
                project_root,
                file_path=write_target_file,
                severity="strict",
                expected=v.field,
                found=v.message,
                retryable=True,
                attempt=attempt,
            )
        prev_violations = violations

    # Budget exhausted.
    log_format_violation(
        project_root,
        file_path=write_target_file,
        severity="hard_failed",
        expected="conforming write within budget",
        found=f"{budget} attempts all failed",
        retryable=False,
        attempt=budget,
    )
    return RetryResult(
        success=False, attempts=budget,
        final_violations=prev_violations or [],
        hard_failure=True,
        reason="budget_exhausted",
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Hermes write-path validator (Phase D)")
    sub = p.add_subparsers(dest="cmd", required=True)

    vbi = sub.add_parser("validate-backlog-item",
                         help="Validate a backlog item JSON on stdin")
    vbi.add_argument("--feedback", action="store_true",
                     help="Print persona-facing feedback text instead of JSON")

    args = p.parse_args(argv)

    if args.cmd == "validate-backlog-item":
        try:
            data = json.loads(sys.stdin.read())
        except json.JSONDecodeError as e:
            print(json.dumps({"valid": False,
                              "violations": [{"field": "_root",
                                              "message": f"invalid JSON: {e}",
                                              "retryable": True}]}))
            return 2
        violations = validate_backlog_item(data)
        if args.feedback:
            print(feedback_for_persona(violations))
            return 0 if not violations else 3
        out = {
            "valid": not violations,
            "violations": [{"field": v.field, "message": v.message,
                            "retryable": v.retryable} for v in violations],
        }
        print(json.dumps(out, indent=2))
        return 0 if not violations else 3

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
