# Runbook
> Project: [Project Name]
> Last updated: [date]
> Owner: [name]
>
> This document tells you how to operate this application in production.
> It exists so you can fix problems at 3am without having to think.

---

## Quick reference

```
Production URL:     https://yourdomain.com
Health check:       https://yourdomain.com/api/health
Railway project:    [project name]
Railway service:    [service name]
Railway dashboard:  https://railway.app/project/[id]
Sentry:             https://sentry.io/[org]/[project]
UptimeRobot:        https://uptimerobot.com/dashboard
Database:           Railway PostgreSQL ([service name])
```

---

## Deploy a new version

**Normal deploy (via CI/CD):**
Push to `main` → GitHub Actions runs tests → Railway deploys automatically.
Watch the deploy: Railway dashboard → your service → **Deployments**.

**Manual deploy (emergency):**
```bash
railway up --service [service-name]
```

**Verify deploy succeeded:**
```bash
curl https://yourdomain.com/api/health
# Expected: {"status":"ok","timestamp":"..."}
```

---

## Roll back a bad deploy

In Railway dashboard:
1. Go to your service → **Deployments**
2. Find the last working deployment
3. Click the three dots menu → **Redeploy**

Railway reploys the previous Docker image — no code changes needed.
The rolled-back version is live within ~2 minutes.

**Verify rollback:**
```bash
curl https://yourdomain.com/api/health
```

---

## Restart the application

```bash
railway restart --service [service-name]
```

Or in Railway dashboard → your service → **Settings** → **Restart**.

Use when: the app is running but behaving incorrectly, memory leak suspected,
config change didn't take effect.

---

## Check application logs

**Railway dashboard (last 7 days):**
Railway dashboard → your service → **Logs**

**Railway CLI (live):**
```bash
railway logs --service [service-name] --tail
```

**Filter for errors:**
```bash
railway logs --service [service-name] | grep -i "error\|exception\|fatal"
```

**Papertrail (beyond 7 days):**
https://papertrailapp.com — search by date range or keyword

---

## Connect to the production database

**Via Railway CLI:**
```bash
railway connect [postgres-service-name]
# Opens a psql session
```

**Via connection string (for Prisma Studio):**
```bash
DATABASE_URL=$(railway variables get DATABASE_URL) npx prisma studio
```

**Important:** Never run destructive queries directly on production.
Always test on a copy of the data first.

---

## Run database migrations in production

Migrations run automatically on deploy via `prisma migrate deploy`.

To run manually (e.g. after a failed deploy):
```bash
railway run npx prisma migrate deploy
```

**Check migration status:**
```bash
railway run npx prisma migrate status
```

**Never run `prisma migrate dev` in production** — it creates new migrations
and can cause data loss.

---

## Rotate secrets and API keys

**When to rotate:** Immediately if a secret is exposed, or on a scheduled
basis (quarterly recommended for production).

**Process:**
1. Generate new key in the relevant service (Clerk, Stripe, etc.)
2. Set the new value in Railway:
   ```bash
   railway variables set KEY_NAME="new-value"
   ```
3. Railway redeploys automatically
4. Verify the app works with the new key
5. Revoke the old key in the service dashboard
6. Update `ENV.md` with any notes (not the actual secret)

**Never commit secrets to git.** If you accidentally do:
1. Rotate the secret immediately
2. Remove from git history: `git filter-repo --path-glob '*.env' --invert-paths`
3. Force push all branches
4. Assume the secret is compromised

---

## Clerk webhook not delivering

**Symptoms:** New users not appearing in database after sign-up.

**Check:**
1. Clerk dashboard → **Webhooks** → your endpoint
2. Check **Recent Deliveries** for failures
3. Check the error message on failed deliveries

**Common causes:**
- Webhook URL changed after domain update
- `CLERK_WEBHOOK_SECRET` rotated in Clerk but not updated in Railway
- Webhook endpoint accidentally protected by Clerk middleware

**Fix:**
```bash
# Update webhook secret if rotated
railway variables set CLERK_WEBHOOK_SECRET="whsec_..."
```

---

## Stripe webhook not delivering

**Symptoms:** Subscriptions not activating after payment.

**Check:**
1. Stripe dashboard → **Developers** → **Webhooks** → your endpoint
2. **Attempts** tab — check for failed deliveries
3. Note the HTTP status code returned

**Common causes:**
- `STRIPE_WEBHOOK_SECRET` mismatch (production webhook vs CLI secret)
- Webhook URL not updated after domain change
- Webhook endpoint protected by Clerk middleware (should be public)

**Fix:**
```bash
# Update webhook secret
railway variables set STRIPE_WEBHOOK_SECRET="whsec_..."

# Manually process a failed payment (if webhook was missed)
railway run npx ts-node scripts/sync-stripe-subscription.ts [subscription-id]
```

---

## Application is slow

**Diagnose:**
1. Check Sentry → **Performance** for slow transactions
2. Check Railway metrics for CPU/memory spikes
3. Check database: look for slow queries

```bash
# Check for slow queries in DB
railway connect [postgres-service-name]
# In psql:
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 seconds';
```

**Common causes:**
- Missing database index (add via Prisma migration)
- N+1 query pattern (fix with `include` in Prisma)
- External API call on the critical path (add timeout + caching)
- Memory leak causing GC pressure (restart buys time, fix the leak)

---

## Railway is down

1. Check Railway status: https://status.railway.app
2. Check your service's health in the dashboard
3. If Railway is the problem: wait, monitor their status page
4. If your service is the problem: check logs for crash reason

**If Railway is fully down:**
- Users see 503 errors — this is outside your control
- Cloudflare may serve a cached version for GET requests
- Update your status page or social media if the outage lasts > 30 minutes

---

## Database backup and restore

**Railway automated backups:**
Railway Pro includes automated backups. For free/hobby plans:

**Manual backup:**
```bash
railway run pg_dump $DATABASE_URL > backup-$(date +%Y%m%d).sql
```

**Restore from backup:**
```bash
railway run psql $DATABASE_URL < backup-20260512.sql
```

**Test your backup works** — do this before you need it, not during an incident.

---

## Who to contact

| Service | Support | Status page |
|---|---|---|
| Railway | support.railway.app | status.railway.app |
| Clerk | clerk.com/support | clerkstatus.com |
| Stripe | support.stripe.com | status.stripe.com |
| Cloudflare | support.cloudflare.com | cloudflarestatus.com |
| Sentry | sentry.io/support | status.sentry.io |
