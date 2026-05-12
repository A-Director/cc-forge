---
name: monitoring-setup
description: >
  Post-deploy monitoring setup. Covers Sentry alerts, Cloudflare analytics,
  UptimeRobot escalation, Railway log retention, and weekly health checks.
  Run at stage 10 MONITOR, immediately after first successful deploy.
model: claude-sonnet-4-6
tools: Read, Write, Bash
---

# Monitoring Setup

You are setting up the production monitoring stack after first deploy.
The goal: know about problems before users tell you.

---

## Sentry alert configuration

In Sentry dashboard → **Alerts** → **Create Alert**:

### Error rate alert
- Alert type: **Issues**
- Conditions: `Number of occurrences` is more than `10` in `1 hour`
- Actions: Send email to [your email]
- Name: `High error rate`

### New issue alert
- Alert type: **Issues**
- Conditions: `A new issue is created`
- Actions: Send email
- Name: `New production error`

### Performance alert
- Alert type: **Metrics**
- Metric: `p95 transaction duration`
- Threshold: greater than `3000ms`
- Actions: Send email
- Name: `Slow response times`

---

## UptimeRobot escalation

In UptimeRobot → **Alert Contacts**:
1. Add your email (already done in Railway setup)
2. Set alert threshold: notify after **2 consecutive failures**
   (avoids false alarms from brief network hiccups)

Add a second monitor for your API health:
- URL: `https://yourdomain.com/api/health`
- Keyword monitoring: look for `"status":"ok"`
- Alert if keyword not found

---

## Cloudflare analytics

In Cloudflare dashboard → **Analytics & Logs**:
- **Web Analytics** — enable for traffic and performance data
- **Security** → **Overview** — check weekly for threat patterns
- **Performance** → **Speed** — track Core Web Vitals

No additional setup needed — Cloudflare captures this automatically
once your domain is proxied.

---

## Railway log retention

Railway keeps 7 days of logs by default. For critical events, set up
log draining to Papertrail (free tier: 100MB/month):

1. Sign up at papertrailapp.com
2. Add system → get the log destination URL
3. In Railway dashboard → **Settings** → **Log Drain**:
   - Add the Papertrail URL

This gives you searchable logs beyond Railway's 7-day window.

---

## Weekly health check command

Add to Hermes commands as `/hermes health`:

```bash
# Run weekly or before any significant change
echo "=== Production Health Check ===" && \
echo "--- App status ---" && \
curl -s https://yourdomain.com/api/health | jq && \
echo "--- Recent errors (check Sentry) ---" && \
echo "Visit: https://sentry.io/[your-org]/[your-project]/" && \
echo "--- Uptime (check UptimeRobot) ---" && \
echo "Visit: https://uptimerobot.com/dashboard" && \
echo "--- Railway metrics ---" && \
railway status && \
echo "--- DB connection ---" && \
railway run npx prisma db execute --stdin <<< "SELECT COUNT(*) FROM users;" && \
echo "=== Done ==="
```

---

## Update MONITORING.md

Update the monitoring document with actual values:

```markdown
# Monitoring

## Services
| Service | URL | Purpose |
|---|---|---|
| App | https://yourdomain.com | Production |
| Health check | https://yourdomain.com/api/health | Uptime probe |
| Railway | https://railway.app/project/[id] | Hosting + logs |
| Sentry | https://sentry.io/[org]/[project] | Error tracking |
| UptimeRobot | https://uptimerobot.com/dashboard | Uptime monitoring |
| Cloudflare | https://dash.cloudflare.com | DNS + analytics |

## Alerts configured
- New Sentry issue → email immediately
- Error rate > 10/hour → email
- p95 latency > 3s → email
- Uptime check fails 2x → email

## Key metrics to watch
- Error rate (Sentry): target < 1% of requests
- p95 response time: target < 1000ms
- Uptime: target > 99.9%
- DB connection pool: check Railway metrics

## Runbook location
See RUNBOOK.md for operational procedures.
```
