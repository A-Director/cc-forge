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

---

## Stack-specific: Python / FastAPI

### [INT-PY-001] FastAPI app starts cleanly with no import errors

**Outcome:** Application boots reliably in production
**Standard:** FastAPI Docs — Application Structure
**Owner:** CTO
**Blocks:** Stage 09 DEPLOY
**Applicability:** Stack: Python/FastAPI
**Status:** not-started
**Evidence:** —

---

### [INT-PY-002] SQLAlchemy models match database schema (no migration drift)

**Outcome:** ORM and database are in sync — no silent data corruption
**Standard:** SQLAlchemy Docs — Migration Best Practices; Alembic Docs
**Owner:** CTO
**Blocks:** Stage 09 DEPLOY
**Applicability:** Stack: Python/SQLAlchemy
**Status:** not-started
**Evidence:** —

---

### [INT-PY-003] Alembic migrations run cleanly on fresh database

**Outcome:** New environment setup is reproducible without manual SQL
**Standard:** Alembic Docs — Migration Environment
**Owner:** CTO
**Blocks:** Stage 09 DEPLOY
**Applicability:** Stack: Python/SQLAlchemy/Alembic
**Status:** not-started
**Evidence:** —

---

### [INT-PY-004] FastAPI dependency injection used for DB sessions

**Outcome:** Database connections properly scoped and closed — no connection leaks
**Standard:** FastAPI Docs — SQL Databases; SQLAlchemy Session Management
**Owner:** CTO
**Blocks:** Stage 08 REVIEW
**Applicability:** Stack: Python/FastAPI/SQLAlchemy
**Status:** not-started
**Evidence:** —

---

## Stack-specific: pgvector

### [INT-PGV-001] pgvector extension enabled and vector similarity search working

**Outcome:** Semantic search over embeddings functional
**Standard:** pgvector Docs — Installation and Usage
**Owner:** CTO
**Blocks:** Stage 09 DEPLOY (when pgvector is in scope)
**Applicability:** Stack: pgvector (Phase 2+)
**Status:** not-applicable
**Evidence:** Deferred to Phase 2 — ADR-AUTO-pgvector

---

## Stack-specific: Fernet / symmetric encryption

### [INT-FNT-001] Fernet key stored in environment variable, never in code

**Outcome:** Encryption key not exposed in repository or logs
**Standard:** cryptography.io Docs — Fernet; OWASP ASVS 4.0 — V2.10.1
**Owner:** Security Auditor
**Blocks:** Stage 09 DEPLOY
**Applicability:** Stack: Python/Fernet encryption
**Status:** not-started
**Evidence:** —

---

### [INT-FNT-002] Fernet key rotation procedure documented in RUNBOOK.md

**Outcome:** Encrypted data can be re-keyed without data loss
**Standard:** cryptography.io Docs — Key Rotation; cc-forge reliability standards
**Owner:** SRE Engineer
**Blocks:** Launch
**Applicability:** Stack: Python/Fernet encryption
**Status:** not-started
**Evidence:** —
