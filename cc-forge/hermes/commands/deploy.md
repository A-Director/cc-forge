---
name: hermes-deploy
description: >
  Run the production deploy sequence. Pre-flight checks, persona gate
  verification, Railway deploy, and post-deploy verification.
  Run with /hermes deploy.
---

# Hermes Deploy

You are running the production deploy sequence. This is not a drill.

## Pre-flight

Check each item. Stop if anything fails:

```bash
# Tests
npm test
echo "Tests: $?"

# Build
npm run build
echo "Build: $?"

# TypeScript
npx tsc --noEmit
echo "TypeScript: $?"

# Lint
npm run lint
echo "Lint: $?"

# Security
npm audit --audit-level=high
echo "Audit: $?"
```

Check gate history:
```bash
cat .cc-forge/state.json | grep gates_passed
```

Verify SRE gate and Security gate have passed. If not:
"Deploy blocked: SRE gate and Security gate must pass before deploy.
Run `/hermes gate review` first."

Check RUNBOOK.md exists:
```bash
test -f RUNBOOK.md && echo "RUNBOOK: ok" || echo "RUNBOOK: MISSING — deploy blocked"
```

## Deploy

If all pre-flight checks pass:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PRE-FLIGHT COMPLETE  ·  All checks passed
  Deploying to production...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Push to main (triggers CI/CD):
```bash
git push origin main
```

Monitor the deploy:
"Watch Railway dashboard → Deployments for build progress.
Run `/hermes verify` after deploy completes (usually 3-5 minutes)."

## Post-deploy verification

```bash
# Health check
curl https://yourdomain.com/api/health

# Verify response
# Expected: {"status":"ok","timestamp":"..."}
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DEPLOY COMPLETE
  ✓ Health check passing
  ✓ Production: https://yourdomain.com

  Watch Sentry for the next 30 minutes for any
  errors triggered by the new deploy.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Update `.cc-forge/state.json` with deploy date.
