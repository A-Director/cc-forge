# Decision Log
> Project: [Project Name]
> Owner: Product Owner
> Last updated: [date]
>
> Every significant technical or product decision recorded here.
> Decision rationale scattered across session journals, code comments,
> and memory is a maintenance liability. This file fixes that.

---

## How to use this log

**When to add an entry:**
- Any technology or library choice with meaningful alternatives
- Any architectural pattern chosen over another
- Any backlog item marked `not-applicable` (mandatory)
- Any persona gate bypassed or deferred (mandatory)
- Any scope decision (feature in vs out of MVP)
- Any security or compliance trade-off accepted

**Who adds entries:**
- Hermes adds automatically when a gate is bypassed or backlog item overridden
- Personas add during gate reviews (see "Decisions to record" in each report)
- The developer adds for technology and scope decisions

**The rule:**
If you have to explain a decision to a new team member,
it belongs in this log. Decisions made once should not be
re-litigated in every future session.

---

## Decision format

```markdown
### [ADR-NNN] Decision title

**Date:** [date]
**Status:** Proposed / Accepted / Superseded / Deprecated
**Decided by:** [Developer / Persona name]
**Standard:** [Standard reference if applicable — or "cc-forge opinionated"]

**Context:**
[What situation forced this decision? What problem were we solving?]

**Decision:**
[What was chosen — be specific]

**Rationale:**
[Why this option over the alternatives. Be honest — "it was faster"
is a valid rationale if that's the truth]

**Alternatives considered:**
| Option | Rejected because |
|---|---|
| [Option A] | [Reason] |
| [Option B] | [Reason] |

**Consequences:**
[What does this decision make easier? What does it make harder?
What debt does it create?]

**Review trigger:**
[What would cause us to revisit this decision?
e.g. "If Railway pricing increases significantly" or "If we need SOC2"]
```

---

## Technology decisions

<!-- Stack, library, and infrastructure choices -->

### [ADR-001] Template — replace with real decisions

**Date:** [date]
**Status:** Accepted
**Decided by:** Developer

**Context:** [Context]

**Decision:** [Decision]

**Rationale:** [Rationale]

**Alternatives considered:**
| Option | Rejected because |
|---|---|
| [Option] | [Reason] |

**Consequences:** [Consequences]

**Review trigger:** [Trigger]

---

## Architecture decisions

<!-- Structural and pattern choices -->

---

## Product and scope decisions

<!-- Feature in/out of scope, MVP boundaries, user-facing trade-offs -->

---

## Security and compliance decisions

<!-- Any accepted risk or deferred security item — must also be in RISKS.md -->

---

## Overridden backlog items

<!-- When a backlog item is marked not-applicable, the decision lives here -->

---

## Decision summary

| ID | Decision | Date | Status |
|---|---|---|---|
| ADR-001 | [Template] | [date] | Accepted |

---

## Argus checks this log for:
- Any backlog override without a corresponding ADR
- Any gate bypass without a corresponding ADR
- ADRs marked Proposed for more than 7 days (needs resolution)
- ADRs that should be superseded based on recent stack changes
