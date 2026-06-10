# Backlog — 02 Development
> Owner: CTO + QA SME
> Standard references: Google Engineering Practices · SOLID · Vitest/Jest docs
>
> Definition of Done: Architecture reviewed by CTO (PASS/CONDITIONAL),
> test coverage meets minimums per standards/testing.md, TypeScript strict
> with zero errors, no CRITICAL tech debt unresolved.

---

## Universal items

### [DEV-001] Service layer separation enforced — routes call services, services call DB

- Outcome: Business logic testable in isolation, not buried in route handlers
- Standard: Google Engineering Practices — Service Layer; SOLID Single Responsibility
- Owner: cto
- Blocks: Stage 08 REVIEW
- Applicability: Universal
- Phase: 1 (MVP)
- Status: not-started
- Evidence: —
---

### [DEV-002] TypeScript strict mode enabled, zero `any` types in production code

- Outcome: Type safety enforced at compile time, no runtime type surprises
- Standard: TypeScript Strict Mode — tsconfig strict: true
- Owner: cto
- Blocks: Stage 08 REVIEW
- Applicability: Stack: TypeScript
- Phase: 2 (Beta)
- Status: not-started
- Evidence: —
---

### [DEV-003] All functions under 50 lines, files under 300 lines

- Outcome: Code readable and maintainable without deep context
- Standard: Google Engineering Practices — Function Length
- Owner: cto
- Blocks: Stage 08 REVIEW
- Applicability: Universal
- Phase: 2 (Beta)
- Status: not-started
- Evidence: —
---

### [DEV-004] No console.log statements in production code

- Outcome: Production logs are structured and intentional
- Standard: cc-forge coding standards — Logging
- Owner: cto
- Blocks: Stage 09 DEPLOY
- Applicability: Universal
- Phase: 2 (Beta)
- Status: not-started
- Evidence: —
---

### [DEV-005] No TODO/FIXME/HACK comments in production code paths

- Outcome: Known issues tracked in Taskmaster, not buried in code comments
- Standard: cc-forge coding standards — Comments
- Owner: cto
- Blocks: Launch
- Applicability: Universal
- Phase: 4 (Launch)
- Status: not-started
- Evidence: —
---

### [DEV-TEST-001] Unit test coverage ≥ 80% on service layer

- Outcome: Business logic regression-protected by automated tests
- Standard: cc-forge testing standards — Coverage targets
- Owner: qa-sme
- Blocks: Stage 08 REVIEW
- Applicability: Universal
- Phase: 2 (Beta)
- Status: not-started
- Evidence: —
---

### [DEV-TEST-002] All webhook handlers have integration tests

- Outcome: Webhook processing regressions caught before reaching production
- Standard: cc-forge testing standards — Webhook coverage
- Owner: qa-sme
- Blocks: Stage 09 DEPLOY
- Applicability: Universal
- Phase: 3 (Pilot)
- Status: not-started
- Evidence: —
---

### [DEV-TEST-003] Auth flow tested end-to-end (sign up, sign in, protected route)

- Outcome: Core auth regression detectable before deploy
- Standard: cc-forge testing standards — Critical flow coverage
- Owner: qa-sme
- Blocks: Stage 09 DEPLOY
- Applicability: Universal
- Phase: 2 (Beta)
- Status: not-started
- Evidence: —
---

### [DEV-CI-001] CI pipeline runs tests before every merge to main

- Outcome: No regression ships without automated test verification
- Standard: DORA metrics — Change Failure Rate reduction
- Owner: qa-sme
- Blocks: Stage 09 DEPLOY
- Applicability: Universal
- Phase: 2 (Beta)
- Status: not-started
- Evidence: —
---

### [DEV-CI-002] CI pipeline runs npm audit before every merge

- Outcome: Known vulnerabilities blocked from shipping automatically
- Standard: OWASP Top 10 — A06 Vulnerable Components
- Owner: cto
- Blocks: Stage 09 DEPLOY
- Applicability: Stack: Node.js
- Phase: 3 (Pilot)
- Status: not-started
- Evidence: —
---
