---
name: stripe-billing-setup
description: >
  Pre-baked Stripe billing setup for Next.js 14+ with Clerk auth.
  Covers installation, products/prices, checkout session, customer portal,
  webhook handler, subscription status in database, and billing-gated routes.
  Run at stage 07 BILLING. Requires Clerk (stage 06) to be complete first.
model: claude-sonnet-4-6
tools: Read, Write, Bash, Glob, Grep
---

# Stripe Billing Setup

You are setting up Stripe billing for a Next.js 14+ project that already
has Clerk authentication. This is production-ready billing — not a demo.

Before starting, verify Clerk is set up:
```bash
cat package.json | grep clerk
cat src/middleware.ts 2>/dev/null | grep clerk
```

If Clerk is not set up, stop and run the Clerk setup agent first.

---

## Phase 1: Install and configure

### 1.1 Install Stripe
```bash
npm install stripe @stripe/stripe-js
```

### 1.2 Environment variables
Add to `.env.local`:
```bash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...

# Add after creating products in Stripe dashboard:
STRIPE_PRICE_ID_PRO_MONTHLY=price_...
STRIPE_PRICE_ID_PRO_YEARLY=price_...  # if offering annual
```

Update `ENV.md` and `.env.example`.

### 1.3 Stripe client utilities
```typescript
// src/lib/stripe.ts
import Stripe from 'stripe'

export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2024-12-18.acacia',
  typescript: true,
})
```

```typescript
// src/lib/stripe-client.ts (browser-safe)
import { loadStripe } from '@stripe/stripe-js'

let stripePromise: ReturnType<typeof loadStripe>

export function getStripe() {
  if (!stripePromise) {
    stripePromise = loadStripe(
      process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!
    )
  }
  return stripePromise
}
```

---

## Phase 2: Database schema

Add subscription tracking to Prisma schema:

```prisma
model User {
  // ... existing fields ...
  subscription   Subscription?
  stripeCustomerId String? @unique
}

model Subscription {
  id                   String    @id @default(cuid())
  userId               String    @unique
  user                 User      @relation(fields: [userId], references: [id], onDelete: Cascade)

  stripeSubscriptionId String    @unique
  stripeCustomerId     String
  stripePriceId        String
  stripeCurrentPeriodEnd DateTime

  status               SubscriptionStatus @default(INACTIVE)
  plan                 String             @default("free")

  createdAt            DateTime  @default(now())
  updatedAt            DateTime  @updatedAt
}

enum SubscriptionStatus {
  ACTIVE
  INACTIVE
  PAST_DUE
  CANCELED
  TRIALING
}
```

Run migration:
```bash
npx prisma migrate dev --name add-subscriptions-table
```

---

## Phase 3: Products and prices

Create products in Stripe dashboard OR via API:

```typescript
// scripts/setup-stripe-products.ts
// Run once: npx ts-node scripts/setup-stripe-products.ts

import { stripe } from '../src/lib/stripe'

async function main() {
  // Create product
  const product = await stripe.products.create({
    name: 'Pro',
    description: 'Full access to all features',
  })

  // Monthly price
  const monthlyPrice = await stripe.prices.create({
    product: product.id,
    unit_amount: 1900, // $19.00 in cents
    currency: 'usd',
    recurring: {
      interval: 'month',
    },
  })

  // Annual price (optional)
  const yearlyPrice = await stripe.prices.create({
    product: product.id,
    unit_amount: 19000, // $190.00 in cents
    currency: 'usd',
    recurring: {
      interval: 'year',
    },
  })

  console.log('Monthly price ID:', monthlyPrice.id)
  console.log('Yearly price ID:', yearlyPrice.id)
  console.log('Add these to your .env.local')
}

main().catch(console.error)
```

---

## Phase 4: Checkout session

### 4.1 Create checkout API route
```typescript
// src/app/api/billing/checkout/route.ts
import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import { stripe } from '@/lib/stripe'
import { db } from '@/lib/db'

export async function POST(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const { priceId } = await req.json()

  if (!priceId) {
    return NextResponse.json({ error: 'priceId required' }, { status: 400 })
  }

  // Get or create Stripe customer
  const user = await db.user.findUnique({
    where: { clerkId: userId },
  })

  if (!user) {
    return NextResponse.json({ error: 'User not found' }, { status: 404 })
  }

  let customerId = user.stripeCustomerId

  if (!customerId) {
    const customer = await stripe.customers.create({
      email: user.email,
      metadata: {
        clerkId: userId,
        userId: user.id,
      },
    })
    customerId = customer.id

    await db.user.update({
      where: { id: user.id },
      data: { stripeCustomerId: customerId },
    })
  }

  // Create checkout session
  const session = await stripe.checkout.sessions.create({
    customer: customerId,
    mode: 'subscription',
    payment_method_types: ['card'],
    line_items: [{ price: priceId, quantity: 1 }],
    success_url: `${process.env.NEXT_PUBLIC_APP_URL}/billing/success?session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `${process.env.NEXT_PUBLIC_APP_URL}/billing`,
    subscription_data: {
      metadata: {
        clerkId: userId,
        userId: user.id,
      },
    },
  })

  return NextResponse.json({ url: session.url })
}
```

### 4.2 Pricing page component
```typescript
// src/app/billing/page.tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function BillingPage() {
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  async function handleSubscribe(priceId: string) {
    setLoading(true)
    try {
      const response = await fetch('/api/billing/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ priceId }),
      })
      const { url } = await response.json()
      if (url) router.push(url)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1>Upgrade to Pro</h1>
      <button
        onClick={() => handleSubscribe(process.env.NEXT_PUBLIC_STRIPE_PRICE_ID_PRO_MONTHLY!)}
        disabled={loading}
      >
        {loading ? 'Loading...' : 'Subscribe — $19/month'}
      </button>
    </div>
  )
}
```

---

## Phase 5: Webhook handler

This is the most critical part. The webhook is how your database stays in
sync with Stripe. Get this wrong and users lose access after paying.

```typescript
// src/app/api/billing/webhook/route.ts
import { NextRequest } from 'next/server'
import Stripe from 'stripe'
import { stripe } from '@/lib/stripe'
import { db } from '@/lib/db'

export async function POST(req: NextRequest) {
  const body = await req.text()
  const signature = req.headers.get('stripe-signature')!

  let event: Stripe.Event

  try {
    event = stripe.webhooks.constructEvent(
      body,
      signature,
      process.env.STRIPE_WEBHOOK_SECRET!
    )
  } catch (err) {
    console.error('Stripe webhook verification failed:', err)
    return new Response('Webhook verification failed', { status: 400 })
  }

  // Handle events
  switch (event.type) {
    case 'checkout.session.completed': {
      const session = event.data.object as Stripe.CheckoutSession
      await handleCheckoutComplete(session)
      break
    }
    case 'invoice.payment_succeeded': {
      const invoice = event.data.object as Stripe.Invoice
      await handlePaymentSucceeded(invoice)
      break
    }
    case 'invoice.payment_failed': {
      const invoice = event.data.object as Stripe.Invoice
      await handlePaymentFailed(invoice)
      break
    }
    case 'customer.subscription.updated': {
      const subscription = event.data.object as Stripe.Subscription
      await handleSubscriptionUpdated(subscription)
      break
    }
    case 'customer.subscription.deleted': {
      const subscription = event.data.object as Stripe.Subscription
      await handleSubscriptionDeleted(subscription)
      break
    }
  }

  return new Response('OK', { status: 200 })
}

async function handleCheckoutComplete(session: Stripe.CheckoutSession) {
  const subscription = await stripe.subscriptions.retrieve(
    session.subscription as string
  )

  const userId = subscription.metadata.userId
  if (!userId) return

  await db.subscription.upsert({
    where: { userId },
    create: {
      userId,
      stripeSubscriptionId: subscription.id,
      stripeCustomerId: subscription.customer as string,
      stripePriceId: subscription.items.data[0].price.id,
      stripeCurrentPeriodEnd: new Date(
        subscription.current_period_end * 1000
      ),
      status: 'ACTIVE',
      plan: 'pro',
    },
    update: {
      stripeSubscriptionId: subscription.id,
      stripePriceId: subscription.items.data[0].price.id,
      stripeCurrentPeriodEnd: new Date(
        subscription.current_period_end * 1000
      ),
      status: 'ACTIVE',
      plan: 'pro',
    },
  })
}

async function handlePaymentSucceeded(invoice: Stripe.Invoice) {
  const subscription = await stripe.subscriptions.retrieve(
    invoice.subscription as string
  )

  await db.subscription.update({
    where: { stripeSubscriptionId: subscription.id },
    data: {
      status: 'ACTIVE',
      stripeCurrentPeriodEnd: new Date(
        subscription.current_period_end * 1000
      ),
    },
  })
}

async function handlePaymentFailed(invoice: Stripe.Invoice) {
  const subscription = await stripe.subscriptions.retrieve(
    invoice.subscription as string
  )

  await db.subscription.update({
    where: { stripeSubscriptionId: subscription.id },
    data: { status: 'PAST_DUE' },
  })
}

async function handleSubscriptionUpdated(subscription: Stripe.Subscription) {
  const status = subscription.status === 'active' ? 'ACTIVE'
    : subscription.status === 'past_due' ? 'PAST_DUE'
    : subscription.status === 'trialing' ? 'TRIALING'
    : 'INACTIVE'

  await db.subscription.update({
    where: { stripeSubscriptionId: subscription.id },
    data: {
      status,
      stripePriceId: subscription.items.data[0].price.id,
      stripeCurrentPeriodEnd: new Date(
        subscription.current_period_end * 1000
      ),
    },
  })
}

async function handleSubscriptionDeleted(subscription: Stripe.Subscription) {
  await db.subscription.update({
    where: { stripeSubscriptionId: subscription.id },
    data: { status: 'CANCELED' },
  })
}
```

**Verify the webhook endpoint is in `isPublicRoute` in Clerk middleware.**
This is the most common mistake — Clerk blocks the webhook if it's protected.

---

## Phase 6: Customer portal

Let users manage their own subscription (cancel, update payment, etc.):

```typescript
// src/app/api/billing/portal/route.ts
import { auth } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'
import { stripe } from '@/lib/stripe'
import { db } from '@/lib/db'

export async function POST() {
  const { userId } = await auth()
  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const user = await db.user.findUnique({
    where: { clerkId: userId },
  })

  if (!user?.stripeCustomerId) {
    return NextResponse.json(
      { error: 'No billing account found' },
      { status: 400 }
    )
  }

  const session = await stripe.billingPortal.sessions.create({
    customer: user.stripeCustomerId,
    return_url: `${process.env.NEXT_PUBLIC_APP_URL}/billing`,
  })

  return NextResponse.json({ url: session.url })
}
```

Add `NEXT_PUBLIC_APP_URL` to ENV.md:
```
NEXT_PUBLIC_APP_URL=http://localhost:3000  # production: https://yourdomain.com
```

---

## Phase 7: Subscription access helpers

```typescript
// src/lib/subscription.ts
import { auth } from '@clerk/nextjs/server'
import { db } from '@/lib/db'

export async function getUserSubscription() {
  const { userId } = await auth()
  if (!userId) return null

  const user = await db.user.findUnique({
    where: { clerkId: userId },
    include: { subscription: true },
  })

  return user?.subscription ?? null
}

export async function isSubscribed(): Promise<boolean> {
  const subscription = await getUserSubscription()
  if (!subscription) return false

  const isActive = subscription.status === 'ACTIVE' ||
                   subscription.status === 'TRIALING'
  const isNotExpired = subscription.stripeCurrentPeriodEnd > new Date()

  return isActive && isNotExpired
}

// Use in Server Components and API routes:
// if (!(await isSubscribed())) redirect('/billing')
```

### Billing gate component
```typescript
// src/components/billing-gate.tsx
import { isSubscribed } from '@/lib/subscription'
import { redirect } from 'next/navigation'

export async function BillingGate({
  children
}: {
  children: React.ReactNode
}) {
  const subscribed = await isSubscribed()
  if (!subscribed) redirect('/billing')
  return <>{children}</>
}
```

Usage in a protected page:
```typescript
// src/app/dashboard/pro-feature/page.tsx
import { BillingGate } from '@/components/billing-gate'

export default function ProFeaturePage() {
  return (
    <BillingGate>
      <div>Pro feature content here</div>
    </BillingGate>
  )
}
```

---

## Phase 8: Testing with Stripe CLI

```bash
# Install Stripe CLI
# macOS: brew install stripe/stripe-cli/stripe
# Windows: scoop install stripe

# Login
stripe login

# Forward webhooks to local dev
stripe listen --forward-to localhost:3000/api/billing/webhook

# In another terminal — trigger test events
stripe trigger checkout.session.completed
stripe trigger invoice.payment_succeeded
stripe trigger customer.subscription.deleted
```

Check your database after each trigger to verify the subscription status
updates correctly.

---

## Phase 9: Verification checklist

- [ ] Stripe publishable key loads without errors in browser console
- [ ] Clicking subscribe redirects to Stripe Checkout
- [ ] Test card `4242 4242 4242 4242` completes checkout
- [ ] After checkout, subscription record exists in database with ACTIVE status
- [ ] `isSubscribed()` returns true for the test user
- [ ] Pro feature page accessible after subscribing
- [ ] Customer portal link works (Manage Billing button)
- [ ] Cancellation via portal updates subscription status to CANCELED
- [ ] Webhook signature verification working (check Stripe CLI output)
- [ ] Billing webhook is NOT protected by Clerk middleware

---

## Phase 10: Update project state

After completing setup:

1. Update `.cc-forge/state.json`:
```json
{
  "current_stage": 8,
  "stage_name": "REVIEW"
}
```

2. Update `ARCHITECTURE.md` with billing section:
```markdown
## Billing
Stripe handles all payment processing. Users subscribe via Stripe Checkout.
Subscription status is stored in the Subscription table, updated via webhooks
at /api/billing/webhook. The isSubscribed() helper checks status + expiry.
Never trust client-supplied subscription status — always check the database.
The Stripe Customer Portal at /api/billing/portal handles cancellations and
payment updates without custom UI.
```

3. Record in `DECISIONS.md`:
```markdown
## ADR-00X: Use Stripe for billing
- Decision: Stripe
- Rationale: Industry standard, best documentation, Customer Portal removes
  need for custom cancellation/update UI, webhook-based sync is reliable
- Alternatives: Paddle (better for EU VAT), Lemon Squeezy (simpler but
  less flexible)
```

---

## Common issues

**Webhook returns 401:**
The webhook URL is protected by Clerk middleware. Add `/api/billing/webhook`
to `isPublicRoute` in `src/middleware.ts`.

**`stripe.webhooks.constructEvent` throws:**
- Confirm `STRIPE_WEBHOOK_SECRET` matches the secret shown in Stripe CLI output
  (`whsec_...`) not the Stripe dashboard webhook secret — they're different
  in local dev vs production
- Ensure you're reading the body as raw text (`await req.text()`), not JSON

**Subscription not created after checkout:**
- Check Stripe CLI output for webhook delivery
- Verify `subscription.metadata.userId` is set in the checkout session creation
- Check database logs for constraint violations

**`isSubscribed()` returns false for active subscriber:**
Check `stripeCurrentPeriodEnd` — if it's in the past, the subscription
technically expired. Stripe should have sent `invoice.payment_succeeded`
to extend it — check webhook delivery.
