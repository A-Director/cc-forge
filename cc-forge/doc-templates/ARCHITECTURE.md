# Architecture
> Project: [Project Name]
> Created: [date] | Last updated: [date]
>
> Living document. Update when structural decisions are made.
> Record every significant decision in DECISIONS.md with rationale.

---

## System overview

[2-3 sentences describing what this system does at a high level, who uses
it, and roughly how it works. Someone new to the project should understand
the shape of the system from this paragraph.]

---

## Architecture diagram

```
[User browser]
      │ HTTPS
      ▼
[Cloudflare CDN/WAF]
      │
      ▼
[Railway — Next.js 14 App]
  ├── App Router (pages + layouts)
  ├── API Routes (/api/*)
  ├── Server Components
  └── Client Components
      │
      ├──[Clerk] Auth
      ├──[Stripe] Billing
      └──[Railway PostgreSQL] Database
              │
              └── Prisma ORM
```

Update this diagram as the architecture evolves.

---

## Stack decisions

| Layer | Choice | Version | Rationale |
|---|---|---|---|
| Framework | Next.js (App Router) | 14.x | Fullstack, great DX, Railway support |
| Language | TypeScript | 5.x | Type safety, better tooling |
| Database | PostgreSQL | 15.x | Reliable, Railway co-located |
| ORM | Prisma | 5.x | Type-safe, great migrations |
| Auth | Clerk | latest | Best DX, pre-built UI |
| Billing | Stripe | latest | Industry standard |
| Hosting | Railway | — | Simple deploys, no DevOps |
| DNS/CDN | Cloudflare | — | Free, DDoS protection |
| Error tracking | Sentry | latest | Free tier, great Next.js integration |
| Styling | Tailwind CSS | 3.x | Utility-first, fast iteration |

---

## Data model

[Key entities and their relationships. Update as schema evolves.]

```
User
  ├── clerkId (unique — links to Clerk)
  ├── email
  └── Subscription (one-to-one, optional)
        ├── stripeSubscriptionId
        ├── status (ACTIVE / INACTIVE / PAST_DUE / CANCELED)
        └── stripeCurrentPeriodEnd

[Add your domain entities here]
```

---

## Key flows

### Authentication flow
1. User visits protected route
2. Clerk middleware checks session → redirects to `/sign-in` if none
3. User signs in via Clerk component
4. Clerk creates session, redirects to `/dashboard`
5. Clerk webhook fires `user.created` → syncs to our database

### Billing flow
1. User clicks Subscribe
2. POST `/api/billing/checkout` → creates Stripe Checkout session
3. User completes payment on Stripe-hosted page
4. Stripe fires `checkout.session.completed` webhook
5. Webhook handler creates Subscription record in database
6. User redirected to success page

### Request flow (API)
```
HTTP Request
  → Clerk middleware (auth check)
  → Route handler (validation, auth extract)
  → Service layer (business logic)
  → Prisma (database query)
  → Response
```

---

## Infrastructure

```
Production environment (Railway):
  Service: [app-service-name]
  Database: [postgres-service-name]
  Region: [railway region]
  Auto-deploy: on push to main
  Start command: npx prisma migrate deploy && npm start
```

---

## Security model

- All routes protected by Clerk middleware except: `/`, `/sign-in`, `/sign-up`,
  `/api/webhooks/*`
- All DB queries scoped to authenticated `userId`
- Webhook signatures verified (Stripe + Clerk)
- Secrets in Railway environment variables only
- HTTPS enforced via Cloudflare (Full Strict SSL)

---

## Known limitations and trade-offs

[Document conscious trade-offs and known limitations. This section prevents
the same debates from happening repeatedly.]

- **[Trade-off]:** [What was chosen, what was given up, why this was the
  right call for the current stage]

---
