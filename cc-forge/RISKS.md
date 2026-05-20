# Risk Register
> Project: [Project Name]
> Owner: Product Owner
> Last updated: [date]
>
> Every accepted risk, deferred item, or backlog override is recorded here.
> No risk is silent. If you skip something, it lives here with a review date.

---

## How to use this register

**When to add an entry:**
- A backlog item is marked `not-applicable` without a universal reason
- A persona gate is bypassed or deferred
- A known vulnerability or gap is accepted as a temporary risk
- A security, reliability, or compliance item is intentionally deferred

**Relationship to PRD risk register:**
Some projects maintain a separate risk register in their PRD (e.g. R-1..R-5).
Both can coexist — the PRD risk register covers *product and business* risks,
while this file covers *operational and technical* risks from cc-forge gate
reviews and backlog overrides. Cross-reference by ID when a risk appears in both.

**Who adds entries:**
- Hermes adds automatically when a developer overrides a gate or backlog item
- Any persona can flag a risk during a gate review
- The developer can add directly for known accepted risks

**Review cadence:**
- Every entry has a `Review date` — revisit before that date
- Argus checks this register weekly for overdue reviews
- Product Owner reviews the full register before every launch

---

## Risk format

```markdown
### [RISK-NNN] Risk title

**Category:** Security / Reliability / Compliance / Performance / Business
**Source:** [Backlog item ID] / [Gate] / [Manual]
**Standard:** [Standard reference if applicable]
**Identified:** [date]
**Identified by:** [Persona or developer]

**Description:**
[What the risk is and why it exists]

**Likelihood:** Low / Medium / High
**Impact:** Low / Medium / High  
**Risk level:** [Likelihood × Impact = Low/Medium/High/Critical]

**Mitigation:**
[What is being done to reduce the risk, even if not fully addressed]

**Acceptance rationale:**
[Why this risk is being accepted now — be honest]

**Review date:** [date — must be set, cannot be blank]
**Status:** ACCEPTED / MITIGATED / RESOLVED / OVERDUE
**Resolved:** [date and how, if resolved]
```

---

## Active risks

<!-- Hermes and personas add entries here automatically -->
<!-- Format: newest first -->

### [RISK-001] Template entry — replace with real risks

**Category:** [Category]
**Source:** Manual
**Identified:** [date]
**Identified by:** Developer

**Description:**
[Description]

**Likelihood:** Medium
**Impact:** Medium
**Risk level:** Medium

**Mitigation:** [Mitigation]

**Acceptance rationale:** [Why accepted]

**Review date:** [date]
**Status:** ACCEPTED

---

## Resolved risks

<!-- Move entries here when resolved — don't delete them -->
<!-- Resolved risks are part of the project's decision history -->

---

## Risk summary

| ID | Title | Level | Status | Review date |
|---|---|---|---|---|
| RISK-001 | [Template] | Medium | ACCEPTED | [date] |

---

## Argus checks this register for:
- Any entry with `Review date` in the past and status still ACCEPTED
- Any entry with status OVERDUE
- Any backlog override without a corresponding entry here
- Any critical risk without documented mitigation
