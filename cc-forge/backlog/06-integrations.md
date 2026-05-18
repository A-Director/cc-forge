# Backlog — 06 Integrations
> Owner: CTO + Security Auditor
> Standard references: Clerk Docs · Stripe Docs · Railway Docs
>
> Definition of Done: All stack-specific integrations verified end-to-end
> in production mode. Webhooks delivering. Production keys active.

---

## Stack-specific: Clerk

### [INT-CLK-001] Clerk sign-up and sign-in flows working end-to-end

**Outcome:** Users can create accounts and authenticate reliably
**Standard:** Clerk Docs — Next.js Quickstart
**Owner:** CTO
**Blocks:** Stage 09 DEPLOY
**Applicability:** Stack: Clerk
**Status:** not-started
**Evidence:** —

---

### [INT-CLK-002] Clerk webhook syncing users to application database

**Outcome:** User records in application DB stay in sync with Clerk
**Standard:** Clerk Docs — Webhooks
**Owner:** CTO
**Blocks:** Stage 09 DEPLOY
**Applicability:** Stack: Clerk
**Status:** not-started
**Evidence:** —

---

### [INT-CLK-003] Production domain added to Clerk allowed origins

**Outcome:** Auth works on production domain, not just localhost
**Standard:** Clerk Docs — Production Setup
**Owner:** CTO
**Blocks:** Stage 09 DEPLOY
**Applicability:** Stack: Clerk
**Status:** not-started
**Evidence:** —

---

## Stack-specific: Stripe

### [INT-STR-001] Stripe Checkout creating subscriptions end-to-end

**Outcome:** Users can subscribe and access paid features
**Standard:** Stripe Docs — Checkout Sessions
**Owner:** CTO
**Blocks:** Stage 09 DEPLOY
**Applicability:** Stack: Stripe
**Status:** not-started
**Evidence:** —

---

### [INT-STR-002] Stripe webhooks delivering and updating subscription status in DB

**Outcome:** Subscription state in DB stays in sync with Stripe
**Standard:** Stripe Docs — Webhook Integration
**Owner:** CTO
**Blocks:** Stage 09 DEPLOY
**Applicability:** Stack: Stripe
**Status:** not-started
**Evidence:** —

---

### [INT-STR-003] Customer Portal working for subscription management

**Outcome:** Users can cancel, update payment, and manage subscription without support
**Standard:** Stripe Docs — Customer Portal
**Owner:** CTO
**Blocks:** Launch
**Applicability:** Stack: Stripe
**Status:** not-started
**Evidence:** —

---

### [INT-STR-004] Stripe live-mode end-to-end test with real card completed

**Outcome:** Payment flow verified in production conditions before launch
**Standard:** Stripe Docs — Going Live Checklist
**Owner:** CTO
**Blocks:** Launch
**Applicability:** Stack: Stripe
**Status:** not-started
**Evidence:** —

---
