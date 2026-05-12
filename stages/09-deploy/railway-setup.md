---
name: railway-deploy-setup
description: >
  Railway deployment agent for Next.js 14+ projects with PostgreSQL.
  Covers project setup, environment variables, database provisioning,
  custom domain, Cloudflare DNS, Sentry integration, and CI/CD via
  GitHub Actions. Run at stage 09 DEPLOY.
  Pre-flight: SRE + Security gates must have passed first.
model: claude-sonnet-4-6
tools: Read, Write, Bash, Glob
---

# Railway Deploy Setup

You are deploying a Next.js 14+ project to Railway for the first time.
This is a complete production setup — not a staging environment.

Before starting, verify gates have passed:
```bash
cat .cc-forge/state.json | grep gates_passed
```

If SRE or Security gates have not passed, stop. Run `/hermes gate review`
first. Do not deploy into known gaps.

---

## Pre-flight checklist

Verify all of these before touching Railway:

- [ ] All tests passing: `npm test`
- [ ] Build succeeds locally: `npm run build`
- [ ] No TypeScript errors: `npx tsc --noEmit`
- [ ] No lint errors: `npm run lint`
- [ ] `RUNBOOK.md` exists and is complete
- [ ] `ENV.md` lists every required environment variable
- [ ] `.env.example` is current
- [ ] No secrets in code (grep: `grep -r "sk_live\|pk_live\|password" src/`)
- [ ] `npm audit` has no critical vulnerabilities

If any item fails, stop and fix it before proceeding.

---

## Phase 1: Railway project setup

### 1.1 Install Railway CLI
```bash
# macOS / Linux
brew install railway

# Windows (via Scoop)
scoop install railway

# Or via npm
npm install -g @railway/cli

# Login
railway login
```

### 1.2 Create Railway project
```bash
# From your project root
railway init

# When prompted:
# - Project name: [your-app-name]
# - Environment: production
```

### 1.3 Connect GitHub repo
In the Railway dashboard:
1. Open your project
2. Click **New Service** → **GitHub Repo**
3. Connect your GitHub account if not already connected
4. Select your repository
5. Railway will detect Next.js automatically

Verify the start command Railway detected:
```bash
railway variables get START_COMMAND
# Should be: npm start or next start
```

If not detected correctly, set manually:
```bash
railway variables set START_COMMAND="npm start"
railway variables set BUILD_COMMAND="npm run build"
```

---

## Phase 2: Database provisioning

### 2.1 Add PostgreSQL
In Railway dashboard:
1. Click **New Service** → **Database** → **PostgreSQL**
2. Railway provisions a Postgres instance automatically
3. Click on the Postgres service → **Connect** tab
4. Copy the `DATABASE_URL` connection string

### 2.2 Set DATABASE_URL
```bash
railway variables set DATABASE_URL="postgresql://..."
```

### 2.3 Run migrations on deploy
Create `railway.json` at project root:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "npx prisma migrate deploy && npm start",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

**Important:** `prisma migrate deploy` (not `dev`) for production.
`migrate deploy` applies pending migrations without creating new ones.

### 2.4 Verify database connection
```bash
# Connect to production DB via Railway CLI
railway run npx prisma db pull

# Should pull your existing schema without errors
```

---

## Phase 3: Environment variables

Set every variable from `ENV.md`. Never copy-paste from `.env.local` —
set them explicitly.

```bash
# Application
railway variables set NEXT_PUBLIC_APP_URL="https://yourdomain.com"
railway variables set NODE_ENV="production"

# Clerk (use production keys, not test keys)
railway variables set NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY="pk_live_..."
railway variables set CLERK_SECRET_KEY="sk_live_..."
railway variables set CLERK_WEBHOOK_SECRET="whsec_..."
railway variables set NEXT_PUBLIC_CLERK_SIGN_IN_URL="/sign-in"
railway variables set NEXT_PUBLIC_CLERK_SIGN_UP_URL="/sign-up"
railway variables set NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL="/dashboard"
railway variables set NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL="/dashboard"

# Stripe (use live keys, not test keys)
railway variables set STRIPE_SECRET_KEY="sk_live_..."
railway variables set STRIPE_WEBHOOK_SECRET="whsec_..."
railway variables set NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY="pk_live_..."
railway variables set STRIPE_PRICE_ID_PRO_MONTHLY="price_..."

# Sentry (set up in Phase 5)
railway variables set SENTRY_DSN="https://..."
railway variables set NEXT_PUBLIC_SENTRY_DSN="https://..."
```

Verify all variables are set:
```bash
railway variables
```

Cross-reference with `ENV.md` — every required variable must appear.

---

## Phase 4: Custom domain + Cloudflare

### 4.1 Add domain in Railway
1. Railway dashboard → your service → **Settings** → **Domains**
2. Click **Add Custom Domain**
3. Enter your domain (e.g. `app.yourdomain.com`)
4. Railway provides a CNAME target (e.g. `xxx.up.railway.app`)

### 4.2 Configure Cloudflare DNS
In Cloudflare dashboard for your domain:
1. Go to **DNS** → **Records**
2. Add a CNAME record:
   - Type: `CNAME`
   - Name: `app` (or `@` for root domain)
   - Target: the Railway CNAME value
   - Proxy: **Enabled** (orange cloud) ← important for DDoS protection

3. For root domain (`yourdomain.com`), add:
   - Type: `A`
   - Name: `@`
   - Value: `192.0.2.1` (placeholder — Cloudflare will proxy it)
   - Proxy: **Enabled**

   Then add the CNAME for `www`:
   - Type: `CNAME`
   - Name: `www`
   - Target: `yourdomain.com`
   - Proxy: **Enabled**

### 4.3 SSL
Railway provisions SSL automatically via Let's Encrypt.
Cloudflare adds an additional SSL layer.

Set Cloudflare SSL mode to **Full (strict)**:
- Cloudflare dashboard → **SSL/TLS** → **Overview**
- Select **Full (strict)**

### 4.4 Update NEXT_PUBLIC_APP_URL
```bash
railway variables set NEXT_PUBLIC_APP_URL="https://yourdomain.com"
```

Redeploy after setting this — it affects Stripe redirect URLs and Clerk.

### 4.5 Update Clerk allowed origins
In Clerk dashboard → **Settings** → **Domains**:
- Add your production domain
- Add `https://yourdomain.com` to allowed origins

### 4.6 Update Stripe webhook endpoint
In Stripe dashboard → **Developers** → **Webhooks**:
- Add endpoint: `https://yourdomain.com/api/billing/webhook`
- Events to send: `checkout.session.completed`, `invoice.payment_succeeded`,
  `invoice.payment_failed`, `customer.subscription.updated`,
  `customer.subscription.deleted`
- Copy the signing secret → update `STRIPE_WEBHOOK_SECRET` in Railway

---

## Phase 5: Sentry error tracking

### 5.1 Create Sentry project
1. Sign up at sentry.io (free tier is sufficient)
2. Create a new project → **Next.js**
3. Copy the DSN

### 5.2 Install Sentry
```bash
npm install @sentry/nextjs

# Run the Sentry wizard (configures automatically)
npx @sentry/wizard@latest -i nextjs
```

The wizard creates:
- `sentry.client.config.ts`
- `sentry.server.config.ts`
- `sentry.edge.config.ts`
- Updates `next.config.js`

### 5.3 Verify Sentry config
```typescript
// sentry.client.config.ts
import * as Sentry from '@sentry/nextjs'

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.1,        // 10% of transactions
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0, // 100% of sessions with errors
  environment: process.env.NODE_ENV,
})
```

### 5.4 Test Sentry is working
Add a test route temporarily:
```typescript
// src/app/api/sentry-test/route.ts (delete after testing)
export async function GET() {
  throw new Error('Sentry test error — delete this route')
}
```

Call it, verify the error appears in Sentry dashboard, then delete the file.

---

## Phase 6: CI/CD pipeline

### 6.1 Railway auto-deploy
Railway deploys automatically on push to `main` by default.
Verify in Railway dashboard → **Settings** → **Source** → **Auto Deploy**.

### 6.2 Add Railway token to GitHub
```bash
# Get Railway token
railway whoami --token
```

In GitHub repo → **Settings** → **Secrets and variables** → **Actions**:
- Add `RAILWAY_TOKEN`
- Add `ANTHROPIC_API_KEY` (for Claude Code Action)

### 6.3 Deploy workflow
Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci
      - run: npm run lint
      - run: npx tsc --noEmit
      - run: npm test -- --coverage

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci

      - name: Deploy to Railway
        uses: bervProject/railway-deploy@main
        with:
          railway_token: ${{ secrets.RAILWAY_TOKEN }}
          service: ${{ vars.RAILWAY_SERVICE_NAME }}
```

This ensures tests pass before every deploy. No deploy on failing tests.

---

## Phase 7: Uptime monitoring

### 7.1 UptimeRobot setup
1. Sign up at uptimerobot.com (free tier: 50 monitors, 5-min intervals)
2. Add a new monitor:
   - Monitor type: **HTTPS**
   - URL: `https://yourdomain.com/api/health`
   - Monitoring interval: **5 minutes**
   - Alert contacts: your email

### 7.2 Health check endpoint
```typescript
// src/app/api/health/route.ts
import { NextResponse } from 'next/server'
import { db } from '@/lib/db'

export async function GET() {
  try {
    // Verify DB is reachable
    await db.$queryRaw`SELECT 1`

    return NextResponse.json({
      status: 'ok',
      timestamp: new Date().toISOString(),
      version: process.env.npm_package_version ?? 'unknown',
    })
  } catch (error) {
    return NextResponse.json(
      { status: 'error', message: 'Database unreachable' },
      { status: 503 }
    )
  }
}
```

This health endpoint:
- Returns 200 when everything is working
- Returns 503 when the DB is unreachable
- UptimeRobot alerts you within 5 minutes of an outage

---

## Phase 8: First deploy

```bash
# Trigger first deploy
git add .
git commit -m "chore: production deployment configuration"
git push origin main
```

Watch the deploy in Railway dashboard. Check:
1. Build succeeds (green checkmark)
2. Migrations run without errors
3. Service starts (health check passes)
4. Domain resolves correctly

```bash
# Test production health endpoint
curl https://yourdomain.com/api/health
# Expected: {"status":"ok","timestamp":"..."}
```

---

## Phase 9: Post-deploy verification

Run through every item:

- [ ] `https://yourdomain.com` loads without errors
- [ ] `https://yourdomain.com/api/health` returns `{"status":"ok"}`
- [ ] Sign up flow works end-to-end
- [ ] Sign in flow works end-to-end
- [ ] New user appears in production database
- [ ] Stripe checkout works with a real card (use $1 test product)
- [ ] Stripe webhook delivering to production URL (check Stripe dashboard)
- [ ] Sentry receiving errors (check Sentry dashboard)
- [ ] UptimeRobot monitor showing green
- [ ] SSL certificate valid (green lock in browser)
- [ ] No console errors in browser dev tools

---

## Phase 10: Update project state

```bash
# Update state
cat > .cc-forge/state.json << 'EOF'
{
  "current_stage": 10,
  "stage_name": "MONITOR"
}
EOF
```

Update `RUNBOOK.md` with the production URLs, Railway project name,
and any operational notes discovered during deploy.

Update `MONITORING.md` with:
- UptimeRobot monitor URLs
- Sentry project DSN (non-secret)
- Railway project name and service name
- Health check endpoint URL

Record in `DECISIONS.md`:
```markdown
## ADR-00X: Deploy to Railway
- Decision: Railway
- Rationale: One-click deploy, Postgres co-location, automatic SSL,
  no DevOps overhead for solo/small team
- Alternatives: Vercel (better for pure Next.js, no DB), AWS (more
  control, much more complexity)
```

---

## Common issues

**Build fails on Railway but works locally:**
- Check Node.js version: Railway defaults to latest LTS. Pin in `package.json`:
  ```json
  { "engines": { "node": "20.x" } }
  ```
- Check for environment variables used at build time — they must be set
  in Railway before the build runs

**Migrations fail on deploy:**
- Confirm `DATABASE_URL` is set correctly in Railway
- Run `railway run npx prisma migrate status` to check migration state
- Never run `prisma migrate dev` in production — only `migrate deploy`

**Domain not resolving:**
- DNS propagation takes up to 24 hours (usually minutes with Cloudflare)
- Verify CNAME record in Cloudflare matches exactly what Railway provided
- Check Cloudflare proxy is enabled (orange cloud)

**Stripe webhooks not reaching production:**
- Confirm webhook URL in Stripe dashboard uses `https://`
- Confirm `STRIPE_WEBHOOK_SECRET` in Railway matches the production
  webhook secret (not the Stripe CLI secret from local dev)
- Test delivery in Stripe dashboard → Webhooks → your endpoint → Send test event

**Clerk auth not working in production:**
- Confirm production domain is added in Clerk dashboard → Domains
- Confirm you're using production Clerk keys (`pk_live_`, `sk_live_`),
  not test keys (`pk_test_`, `sk_test_`)
