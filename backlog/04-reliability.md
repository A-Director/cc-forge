# Backlog — 04 Reliability
> Owner: SRE Engineer
> Standard references: Google SRE Book · DORA metrics · AWS Well-Architected
>
> Definition of Done: RUNBOOK.md complete and reviewed by SRE, INCIDENT.md
> written, monitoring active, CI gate blocking merges, SRE gate PASS/CONDITIONAL.
> Hard rule: SRE gate must PASS before any deploy.

---

## Universal items

### [REL-001] RUNBOOK.md exists and covers all operational procedures

**Outcome:** Any incident can be diagnosed and resolved without the original developer
**Standard:** Google SRE Book — Chapter 8: On-Call; cc-forge reliability standards
**Owner:** SRE Engineer
**Blocks:** Stage 09 DEPLOY — HARD BLOCK
**Applicability:** Universal
**Status:** not-started
**Evidence:** —

---

### [REL-002] INCIDENT.md written with severity definitions and response procedures

**Outcome:** Incidents handled consistently — no improvising at 3am
**Standard:** Google SRE Book — Chapter 14: Managing Incidents
**Owner:** SRE Engineer
**Blocks:** Stage 09 DEPLOY
**Applicability:** Universal
**Status:** not-started
**Evidence:** —

---

### [REL-003] Production error tracking active (Sentry or equivalent)

**Outcome:** Every production error visible within minutes of occurrence
**Standard:** Google SRE Book — Chapter 6: Monitoring; DORA — Mean Time to Detect
**Owner:** SRE Engineer
**Blocks:** Stage 09 DEPLOY — HARD BLOCK
**Applicability:** Universal
**Status:** not-started
**Evidence:** —

---

### [REL-004] Uptime monitoring active with alerting configured

**Outcome:** Downtime detected automatically, not via user complaints
**Standard:** Google SRE Book — SLO/SLA; DORA metrics
**Owner:** SRE Engineer
**Blocks:** Stage 09 DEPLOY
**Applicability:** Universal
**Status:** not-started
**Evidence:** —

---

### [REL-005] Health check endpoint implemented and monitored

**Outcome:** Application liveness verifiable without browser access
**Standard:** cc-forge reliability standards — Health Checks
**Owner:** SRE Engineer
**Blocks:** Stage 09 DEPLOY
**Applicability:** Universal
**Status:** not-started
**Evidence:** —

---

### [REL-006] CI/CD pipeline blocks deploy on failing tests

**Outcome:** Regressions cannot ship via automated deploy
**Standard:** DORA metrics — Change Failure Rate
**Owner:** SRE Engineer
**Blocks:** Stage 09 DEPLOY
**Applicability:** Universal
**Status:** not-started
**Evidence:** —

---

### [REL-007] Database backup configured and restoration tested

**Outcome:** Data loss recoverable — backup is only useful if restore works
**Standard:** AWS Well-Architected — Reliability Pillar; RPO/RTO defined
**Owner:** SRE Engineer
**Blocks:** Launch
**Applicability:** Universal
**Status:** not-started
**Evidence:** —

---

### [REL-008] Rollback procedure documented and tested

**Outcome:** Bad deploy recoverable in under 5 minutes
**Standard:** DORA metrics — Mean Time to Restore
**Owner:** SRE Engineer
**Blocks:** Stage 09 DEPLOY
**Applicability:** Universal
**Status:** not-started
**Evidence:** —

---

### [REL-009] Log retention beyond hosting platform default (7 days)

**Outcome:** Incidents diagnosable even when discovered after platform log expiry
**Standard:** Google SRE Book — Chapter 6: Logging
**Owner:** SRE Engineer
**Blocks:** Launch
**Applicability:** Universal
**Status:** not-started
**Evidence:** —

---

## Stack-specific: Railway

### [REL-STK-RWY-001] Railway deploy configured with restart policy on failure

**Outcome:** Transient crashes recover automatically without manual intervention
**Standard:** Railway Docs — Deploy Configuration
**Owner:** SRE Engineer
**Blocks:** Stage 09 DEPLOY
**Applicability:** Stack: Railway
**Status:** not-started
**Evidence:** —

---

### [REL-STK-RWY-002] Railway memory alerting configured (> 80% threshold)

**Outcome:** Memory leak detected before OOM crash
**Standard:** cc-forge reliability standards — Resource Monitoring
**Owner:** SRE Engineer
**Blocks:** Launch
**Applicability:** Stack: Railway
**Status:** not-started
**Evidence:** —

---
