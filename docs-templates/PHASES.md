# PDLC Phases

> Product Development Lifecycle (PDLC) phases for cc-forge projects.
>
> These are **starting defaults** for a typical SaaS-shaped project.
> Treat them as a template, not a contract. `/hermes-backlog-init`
> tunes the per-phase domain bars based on the project's stack and
> shape at init time.

---

## What this is

cc-forge ships two lifecycles that nest:

- **PDLC (outer)** — five product maturity phases. What bar are we
  shooting for right now?
- **SDLC (inner)** — eleven stage activities (`01-idea` → `11-iterate`)
  that recur inside each PDLC phase. What activity are we doing?

Each PDLC phase consumes multiple SDLC cycles. A phase ends when its
exit gate passes (run via `/hermes-phase-gate`); the next phase opens
with a fresh round of SDLC activities at the new bar.

Industry sequence for reference: PoC → Prototype → MVP → Pilot → Beta
→ Launch. cc-forge collapses PoC/Prototype into the start of Phase 1
(MVP) and uses the canonical five phases below.

---

## The five phases

### Phase 1 — MVP

- **Goal:** Prove the core user journey works end-to-end. One critical
  path runs cleanly on staging; the developer is the only user.
- **Exit gate:** Happy path complete for one critical journey ·
  Runs locally + on staging · No production users yet beyond
  developer · Basic security (HTTPS, secrets in env, auth on
  protected routes)
- **In scope:** Core feature, basic auth, basic deploy, error-free
  happy path.
- **Out of scope:** Scale, formal compliance, growth motions, SLAs.
- **Personas active:** Product Owner (scope), CTO (foundational
  architecture), QA (happy-path tests).
- **Typical SDLC stages:** `01-idea` → `05-build`.
- **Domain bars (% target):**
  - 01 Product 80% · 02 Development 60% · 03 Security 20% (basics
    only) · 04 Reliability 10% · 05 Design 20% · 06 Integrations 40%
    · 07 Compliance 0% · 08 Launch 0% · 09 Growth 0% · 10 Operations
    10%

### Phase 2 — Beta

- **Goal:** Real users on the system in a controlled group. Iterate
  on feedback, fix the top friction.
- **Exit gate:** 10+ active testers · Top-3 reported issues
  remediated · Error monitoring + uptime checks live · Auth flows
  audited · No critical Security gate findings open.
- **In scope:** Rate limiting on auth, structured logging, error
  monitoring (Sentry or equivalent), invite/access control,
  feedback loop.
- **Out of scope:** Full compliance (GDPR endpoints), public
  marketing motion, scaling work.
- **Personas active:** + UX SME (friction review), Security
  Auditor (auth + secrets), SRE SME (basic uptime).
- **Typical SDLC stages:** `05-build` + `08-review` cycles.
- **Domain bars:**
  - 01 100% · 02 80% · 03 60% · 04 40% · 05 60% · 06 70% · 07 10% ·
    08 20% · 09 10% · 10 30%

### Phase 3 — Pilot

- **Goal:** Prove the revenue and ops motion at small paid scale.
  Customers depend on the system; operate it like production.
- **Exit gate:** 5–10 paying customers retained 30+ days · No
  Severity-1 incidents in the last 14 days · Runbook + on-call
  rotation in place · Key rotation tested · Stripe (or equivalent)
  billing reconciled.
- **In scope:** Deploy automation, runbooks, incident response,
  secret rotation, billing edge cases, basic ToS.
- **Out of scope:** Public marketing, full GDPR, accessibility AA
  certification.
- **Personas active:** + CFO (margin & burn), SRE (runbook +
  on-call), Legal SME (basic ToS, terms).
- **Typical SDLC stages:** `06-auth`, `07-billing`, `09-deploy`,
  `10-monitor`.
- **Domain bars:**
  - 01 100% · 02 90% · 03 80% · 04 70% · 05 70% · 06 90% · 07 40% ·
    08 50% · 09 20% · 10 60%

### Phase 4 — Launch

- **Goal:** Open the doors to the public. Meet compliance and
  accessibility bars; support a real acquisition motion.
- **Exit gate:** Public landing live · Support inbox + response
  process live · GDPR data-export + delete endpoints shipped (if EU
  users likely) · ToS + Privacy + Cookie consent live · WCAG 2.1 AA
  spot-checked on critical flows.
- **In scope:** GDPR endpoints, ToS/Privacy/Cookie, accessibility,
  public docs, support workflow, marketing pages.
- **Out of scope:** Sustained growth experimentation (Phase 5).
- **Personas active:** + Growth SME (acquisition setup), Legal
  (full compliance), Market Analyst (positioning).
- **Typical SDLC stages:** `08-review`, `09-deploy`, `10-monitor`.
- **Domain bars:**
  - 01–06 ≥ 95% · 07 Compliance 90% · 08 Launch 95% · 09 Growth
    50% · 10 Operations 80%

### Phase 5 — Growth

- **Goal:** Sustained growth, retention, scale. Continuous
  iteration; no terminal exit gate — the phase is steady-state.
- **Exit gate:** None — Growth is ongoing. Periodic re-gating via
  `/hermes-phase-gate` validates that bars don't regress as the
  product scales.
- **In scope:** Experimentation framework, retention features, SEO,
  support automation, scale work, unit economics tracking, data
  retention policy.
- **Out of scope:** Nothing — every domain is fair game.
- **Personas active:** All personas active. Argus runs weekly to
  catch drift. CFO runs weekly on unit economics. Market Analyst
  runs monthly.
- **Typical SDLC stages:** `11-iterate` (continuous).
- **Domain bars:**
  - All domains 95%+ · 09 Growth 80%+ · 10 Operations 90%+

---

## How items map to phases

Each backlog item carries a `**Phase:**` field. The phase answers the
question: **"What's the earliest PDLC phase where a typical
SaaS-shaped project needs this item done?"** — *not* "what domain
does it belong to."

Calibration examples (from cc-forge defaults):

| Item                                       | Domain     | Phase |
|--------------------------------------------|------------|-------|
| HTTPS on all production endpoints          | Security   | 1 MVP |
| Rate limits on auth endpoints              | Security   | 2 Beta |
| Key rotation tested under load             | Security   | 3 Pilot |
| GDPR data export endpoint                  | Compliance | 4 Launch |
| Retention policy on user data              | Compliance | 5 Growth |

Domains do **not** map cleanly to phases. Security items span every
phase (basics in MVP, hardening in Beta, rotation in Pilot, GDPR in
Launch). Only **09 Growth** and (partially) **07 Compliance** map
cleanly to single later phases.

---

## How to use this file

1. `/hermes-init` copies this template into your project as
   `PHASES.md`.
2. `/hermes-backlog-init` reviews your stack and project shape, and
   may tune the per-phase domain bars (e.g. an internal tool needs
   no Cookie consent; an API product de-emphasizes UX Design).
3. `state.json` carries `current_phase` (1–5) alongside
   `current_stage` (01–11). Hermes reads both at session start.
4. Use `/hermes-phase-gate` to advance between phases. Within a
   phase, use `/hermes gate review` for regular SDLC gates.

## Related

- `stages/00-phase-gate.md` — agent that runs the phase transition
- `hermes/commands/phase-gate.md` — `/hermes-phase-gate` spec
- `session-lifecycle/phase-gates.md` — SDLC gates vs PDLC gates
- `backlog/master.md` — current phase + per-phase bars view
