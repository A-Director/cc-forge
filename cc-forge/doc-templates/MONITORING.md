# Monitoring
> Project: [Project Name]
> Last updated: [date]

---

## Services and URLs

| Service | URL | Purpose |
|---|---|---|
| Production | https://yourdomain.com | App |
| Health check | https://yourdomain.com/api/health | Uptime probe |
| Railway | https://railway.app/project/[id] | Hosting, logs, metrics |
| Sentry | https://sentry.io/[org]/[project] | Error tracking |
| UptimeRobot | https://uptimerobot.com/dashboard | Uptime monitoring |
| Cloudflare | https://dash.cloudflare.com | DNS, CDN, analytics |
| Papertrail | https://papertrailapp.com | Log retention |

---

## Alerts configured

| Alert | Threshold | Channel | Action |
|---|---|---|---|
| App unreachable | 2 consecutive failures | Email | Check RUNBOOK, roll back if needed |
| New Sentry error | Any new issue | Email | Triage in Sentry |
| Error spike | > 10 errors/hour | Email | Check Sentry, assess severity |
| Slow responses | p95 > 3000ms | Email | Check DB queries, Railway metrics |

---

## Key metrics

| Metric | Healthy | Warning | Critical |
|---|---|---|---|
| Uptime | > 99.9% | 99–99.9% | < 99% |
| p95 response time | < 1000ms | 1000–3000ms | > 3000ms |
| Error rate | < 0.1% | 0.1–1% | > 1% |
| DB connections | < 15 | 15–18 | > 18 |

---

## Weekly health check

Run `/hermes health` every Monday morning:
- App health endpoint responds
- No unresolved P0/P1 Sentry issues
- Uptime was > 99.9% last week
- Railway costs within expected range
- No failed webhook deliveries (Stripe + Clerk)

---

## On-call

Solo developer: You are always on-call.
Check UptimeRobot and Sentry every morning.
Set up mobile push notifications for P0 alerts.
