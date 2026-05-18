# Backlog — 03 Security
> Owner: Security Auditor
> Standard references: OWASP Top 10 · OWASP ASVS 4.0 · NIST CSF
>
> Definition of Done: All applicable items are `done` with evidence,
> or `not-applicable` with a decision record. Security Auditor gate
> has returned PASS or CONDITIONAL outcome. No CRITICAL items unresolved.

---

## Universal items (apply to every project)

### [SEC-001] All API routes protected by authentication middleware

**Outcome:** No unauthenticated user can access protected data or actions
**Standard:** OWASP ASVS 4.0 — V4.1.1
**Owner:** Security Auditor
**Blocks:** Stage 09 DEPLOY
**Applicability:** Universal
**Status:** not-started
**Evidence:** —

---

### [SEC-002] All database queries scoped to authenticated user ID

**Outcome:** A user cannot access another user's data by manipulating IDs
**Standard:** OWASP ASVS 4.0 — V4.2.1 (Horizontal Privilege Escalation)
**Owner:** Security Auditor
**Blocks:** Stage 09 DEPLOY
**Applicability:** Universal
**Status:** not-started
**Evidence:** —

---

### [SEC-003] No secrets or API keys hardcoded in source files

**Outcome:** Repository can be made public without exposing credentials
**Standard:** OWASP Top 10 2021 — A02 Cryptographic Failures
**Owner:** Security Auditor
**Blocks:** Stage 09 DEPLOY
**Applicability:** Universal
**Status:** not-started
**Evidence:** —

---

### [SEC-004] .env file is in .gitignore and never committed

**Outcome:** Environment secrets cannot be exposed via git history
**Standard:** OWASP ASVS 4.0 — V2.10.1
**Owner:** Security Auditor
**Blocks:** Stage 09 DEPLOY
**Applicability:** Universal
**Status:** not-started
**Evidence:** —

---

### [SEC-005] All user input validated at the API boundary

**Outcome:** Malformed or malicious input is rejected before reaching business logic
**Standard:** OWASP Top 10 2021 — A03 Injection
**Owner:** Security Auditor
**Blocks:** Stage 09 DEPLOY
**Applicability:** Universal
**Status:** not-started
**Evidence:** —

---

### [SEC-006] Error messages do not expose stack traces to users

**Outcome:** Internal system details not visible to potential attackers
**Standard:** OWASP ASVS 4.0 — V7.4.1
**Owner:** Security Auditor
**Blocks:** Stage 09 DEPLOY
**Applicability:** Universal
**Status:** not-started
**Evidence:** —

---

### [SEC-007] npm audit shows no high or critical vulnerabilities

**Outcome:** No known exploitable vulnerabilities in dependencies
**Standard:** OWASP Top 10 2021 — A06 Vulnerable Components
**Owner:** Security Auditor
**Blocks:** Stage 09 DEPLOY
**Applicability:** Universal
**Status:** not-started
**Evidence:** —

---

### [SEC-008] HTTPS enforced — no HTTP endpoints in production

**Outcome:** All traffic encrypted in transit
**Standard:** OWASP ASVS 4.0 — V9.1.1
**Owner:** Security Auditor
**Blocks:** Stage 09 DEPLOY
**Applicability:** Universal
**Status:** not-started
**Evidence:** —

---

### [SEC-009] CORS configured correctly — not wildcard in production

**Outcome:** Cross-origin requests restricted to known trusted origins
**Standard:** OWASP ASVS 4.0 — V14.4.8
**Owner:** Security Auditor
**Blocks:** Stage 09 DEPLOY
**Applicability:** Universal
**Status:** not-started
**Evidence:** —

---

### [SEC-010] Auth events logged (login, logout, failed attempts)

**Outcome:** Security incidents detectable via audit trail
**Standard:** OWASP ASVS 4.0 — V7.2.1
**Owner:** Security Auditor
**Blocks:** Launch
**Applicability:** Universal
**Status:** not-started
**Evidence:** —

---

### [SEC-011] Rate limiting on authentication endpoints

**Outcome:** Brute force attacks on login are mitigated
**Standard:** OWASP ASVS 4.0 — V4.2.2
**Owner:** Security Auditor
**Blocks:** Public launch (not beta)
**Applicability:** Universal
**Status:** not-started
**Evidence:** —

---

### [SEC-012] Content Security Policy (CSP) headers configured

**Outcome:** XSS attack surface reduced via browser-enforced policy
**Standard:** OWASP ASVS 4.0 — V14.4.3
**Owner:** Security Auditor
**Blocks:** Public launch (not beta)
**Applicability:** Universal
**Status:** not-started
**Evidence:** —

---

## Stack-specific: Clerk

### [SEC-STK-CLK-001] Clerk middleware applied to all protected routes

**Outcome:** No Clerk-authenticated route is accidentally public
**Standard:** Clerk Security Docs — Middleware Configuration
**Owner:** Security Auditor
**Blocks:** Stage 09 DEPLOY
**Applicability:** Stack: Clerk
**Status:** not-started
**Evidence:** —

---

### [SEC-STK-CLK-002] Clerk webhook signature verified before processing

**Outcome:** Webhook cannot be spoofed by external actor
**Standard:** Clerk Security Docs — Webhook Verification
**Owner:** Security Auditor
**Blocks:** Stage 09 DEPLOY
**Applicability:** Stack: Clerk
**Status:** not-started
**Evidence:** —

---

### [SEC-STK-CLK-003] Production Clerk keys used in production (not test keys)

**Outcome:** Production auth uses production-grade credentials
**Standard:** Clerk Docs — Environment Keys
**Owner:** Security Auditor
**Blocks:** Stage 09 DEPLOY
**Applicability:** Stack: Clerk
**Status:** not-started
**Evidence:** —

---

## Stack-specific: Stripe

### [SEC-STK-STR-001] Stripe webhook signature verified via constructEvent

**Outcome:** Payment webhooks cannot be forged
**Standard:** Stripe Security Docs — Webhook Signatures; OWASP ASVS V9.2.1
**Owner:** Security Auditor
**Blocks:** Stage 09 DEPLOY
**Applicability:** Stack: Stripe
**Status:** not-started
**Evidence:** —

---

### [SEC-STK-STR-002] Prices and amounts set server-side only

**Outcome:** Users cannot manipulate payment amounts from the client
**Standard:** Stripe Security Best Practices — Amount Validation
**Owner:** Security Auditor
**Blocks:** Stage 09 DEPLOY
**Applicability:** Stack: Stripe
**Status:** not-started
**Evidence:** —

---

### [SEC-STK-STR-003] Payment data never logged or stored directly

**Outcome:** PCI DSS scope minimised — card data never touches our servers
**Standard:** PCI DSS v4.0 — Requirement 3
**Owner:** Security Auditor
**Blocks:** Stage 09 DEPLOY
**Applicability:** Stack: Stripe
**Status:** not-started
**Evidence:** —

---

## Stack-specific: Railway

### [SEC-STK-RWY-001] All production secrets in Railway environment variables

**Outcome:** Secrets not in code, not in Railway config files, not in git
**Standard:** cc-forge security standards — Secrets Management
**Owner:** Security Auditor
**Blocks:** Stage 09 DEPLOY
**Applicability:** Stack: Railway
**Status:** not-started
**Evidence:** —

---

## Optional items

### [SEC-OPT-001] Two-factor authentication available for users

**Outcome:** Users can protect their accounts with 2FA
**Standard:** OWASP ASVS 4.0 — V2.8.1
**Owner:** Security Auditor
**Blocks:** Not blocking — enhancement
**Applicability:** Optional: SaaS products with sensitive user data
**Status:** not-started
**Evidence:** —
