# Incident Response
> Project: [Project Name]
>
> What to do when things break in production.
> Read RUNBOOK.md for operational procedures.

---

## Severity definitions

| Level | Definition | Response time |
|---|---|---|
| **P0 — Critical** | Production is down for all users, or data loss occurring | Immediate |
| **P1 — High** | Core feature broken for most users, or security incident | Within 1 hour |
| **P2 — Medium** | Feature degraded for some users, workaround exists | Within 4 hours |
| **P3 — Low** | Minor issue, cosmetic, or edge case | Next sprint |

---

## How to know it's broken

**You find out:**
- UptimeRobot alert email (P0 — app is unreachable)
- Sentry alert email (P1/P2 — error spike or new critical error)
- User reports (check email, support channel)

**You check:**
```bash
curl https://yourdomain.com/api/health
# If this fails: P0
# If this returns error details: P1
```

---

## First response (first 5 minutes)

1. **Confirm the incident** — reproduce the issue yourself
2. **Assess severity** — use the table above
3. **Check recent deploys** — was there a deploy in the last hour?
   ```bash
   railway logs --service [name] | grep "deploy\|start"
   ```
4. **Check Sentry** — what errors are firing?
5. **Decision point:**
   - P0/P1 from a recent deploy → **roll back immediately** (see RUNBOOK.md)
   - P0/P1 not from a deploy → investigate

---

## Roll back procedure

See RUNBOOK.md → "Roll back a bad deploy"

Roll back first, investigate second. A 5-minute outage with a rollback
is better than a 2-hour outage while you investigate.

---

## Communicating during an incident

**For P0/P1:** Post an update to users within 15 minutes.

Status message template:
```
We're aware of an issue affecting [feature]. Our team is investigating.
We'll provide an update within [timeframe]. We apologize for the inconvenience.
```

Update every 30 minutes until resolved:
```
Update: We've identified the issue ([brief description]) and are working on a fix.
Estimated resolution: [time].
```

Resolution message:
```
The issue affecting [feature] has been resolved as of [time].
[Brief explanation of what happened and what was fixed.]
We apologize for the disruption.
```

---

## Post-incident review

After every P0 or P1, within 48 hours:

1. **Timeline** — what happened, in order, with timestamps
2. **Root cause** — the actual underlying cause (not the symptom)
3. **Contributing factors** — what made this possible
4. **What we got right** — detection, response, communication
5. **What we got wrong** — and what we'll change
6. **Action items** — specific tasks with owners and due dates

Post-incident reviews are blameless. The goal is system improvement,
not fault assignment.

---
