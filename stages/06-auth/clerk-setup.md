---
name: clerk-auth-setup
description: >
  Pre-baked Clerk authentication setup agent for Next.js 14+ App Router.
  Covers installation, middleware, protected routes, user sync to database,
  and organisation/role-based access. Run at stage 06 AUTH.
  Never start from scratch — use this every time.
model: claude-sonnet-4-6
tools: Read, Write, Bash, Glob, Grep
---

# Clerk Authentication Setup

You are setting up Clerk authentication for a Next.js 14+ App Router project.
This is a complete, production-ready setup — not a tutorial quickstart.
Follow every step. Do not skip sections because they look optional.

---

## Pre-flight checks

Before starting, verify:
```bash
# Confirm Next.js version
cat package.json | grep '"next"'

# Confirm App Router structure
ls src/app 2>/dev/null || ls app 2>/dev/null

# Check if Clerk is already partially installed
cat package.json | grep clerk
```

If Clerk is already partially installed, read existing implementation
before proceeding — do not overwrite without understanding what exists.

---

## Phase 1: Install and configure

### 1.1 Install Clerk
```bash
npm install @clerk/nextjs
```

### 1.2 Environment variables
Add to `.env.local`:
```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...

# Sign-in/up redirect URLs
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/dashboard
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/dashboard
```

Update `ENV.md` with these variable names and descriptions.
Update `.env.example` with empty values.

### 1.3 Middleware
Create `src/middleware.ts` (or `middleware.ts` at root):

```typescript
import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

const isPublicRoute = createRouteMatcher([
  '/',
  '/sign-in(.*)',
  '/sign-up(.*)',
  '/api/webhooks(.*)',   // webhooks must be public
  '/api/billing/webhook' // Stripe webhook must be public
])

export default clerkMiddleware((auth, request) => {
  if (!isPublicRoute(request)) {
    auth().protect()
  }
})

export const config = {
  matcher: [
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    '/(api|trpc)(.*)',
  ],
}
```

**Critical:** The matcher excludes static files and includes all API routes.
Webhooks must be in `isPublicRoute` — Clerk auth will reject webhook calls.

### 1.4 Root layout
Wrap the root layout with `ClerkProvider`:

```typescript
// src/app/layout.tsx
import { ClerkProvider } from '@clerk/nextjs'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: '[App Name]',
  description: '[App Description]',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body>{children}</body>
      </html>
    </ClerkProvider>
  )
}
```

---

## Phase 2: Auth pages

### 2.1 Sign-in page
```typescript
// src/app/sign-in/[[...sign-in]]/page.tsx
import { SignIn } from '@clerk/nextjs'

export default function SignInPage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <SignIn />
    </div>
  )
}
```

### 2.2 Sign-up page
```typescript
// src/app/sign-up/[[...sign-up]]/page.tsx
import { SignUp } from '@clerk/nextjs'

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <SignUp />
    </div>
  )
}
```

### 2.3 User button component (for navbar)
```typescript
// src/components/user-button.tsx
import { UserButton } from '@clerk/nextjs'

export function NavUserButton() {
  return (
    <UserButton
      afterSignOutUrl="/"
      appearance={{
        elements: {
          avatarBox: 'h-8 w-8'
        }
      }}
    />
  )
}
```

---

## Phase 3: Server-side auth usage

### 3.1 Getting the current user in Server Components
```typescript
import { auth, currentUser } from '@clerk/nextjs/server'

// Option A: Get userId only (cheap, use for auth checks)
export default async function Page() {
  const { userId } = await auth()
  if (!userId) redirect('/sign-in')
  // ...
}

// Option B: Get full user (more expensive, use when you need user data)
export default async function ProfilePage() {
  const user = await currentUser()
  if (!user) redirect('/sign-in')
  return <div>Hello {user.firstName}</div>
}
```

### 3.2 Getting the current user in API routes
```typescript
import { auth } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'

export async function GET() {
  const { userId } = await auth()

  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  // Always scope data queries to userId
  const data = await db.items.findMany({
    where: { userId } // NEVER trust client-supplied userId
  })

  return NextResponse.json(data)
}
```

### 3.3 Route handler with full auth context
```typescript
import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'

export async function POST(req: NextRequest) {
  const { userId, orgId, orgRole } = await auth()

  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  // orgId and orgRole are available if using Clerk Organizations
  const body = await req.json()

  // ... handle request
}
```

---

## Phase 4: Database sync

Clerk is the auth provider — your database is the data store.
Sync Clerk user data to your database via webhook.

### 4.1 Webhook endpoint
```typescript
// src/app/api/webhooks/clerk/route.ts
import { Webhook } from 'svix'
import { headers } from 'next/headers'
import { WebhookEvent } from '@clerk/nextjs/server'
import { db } from '@/lib/db'

export async function POST(req: Request) {
  const WEBHOOK_SECRET = process.env.CLERK_WEBHOOK_SECRET

  if (!WEBHOOK_SECRET) {
    throw new Error('CLERK_WEBHOOK_SECRET not set in environment variables')
  }

  // Verify webhook signature
  const headerPayload = headers()
  const svix_id = headerPayload.get('svix-id')
  const svix_timestamp = headerPayload.get('svix-timestamp')
  const svix_signature = headerPayload.get('svix-signature')

  if (!svix_id || !svix_timestamp || !svix_signature) {
    return new Response('Missing svix headers', { status: 400 })
  }

  const payload = await req.json()
  const body = JSON.stringify(payload)

  const wh = new Webhook(WEBHOOK_SECRET)
  let evt: WebhookEvent

  try {
    evt = wh.verify(body, {
      'svix-id': svix_id,
      'svix-timestamp': svix_timestamp,
      'svix-signature': svix_signature,
    }) as WebhookEvent
  } catch (err) {
    console.error('Webhook verification failed:', err)
    return new Response('Webhook verification failed', { status: 400 })
  }

  // Handle events
  const eventType = evt.type

  if (eventType === 'user.created') {
    await db.user.create({
      data: {
        clerkId: evt.data.id,
        email: evt.data.email_addresses[0]?.email_address ?? '',
        firstName: evt.data.first_name ?? '',
        lastName: evt.data.last_name ?? '',
        imageUrl: evt.data.image_url ?? '',
      },
    })
  }

  if (eventType === 'user.updated') {
    await db.user.update({
      where: { clerkId: evt.data.id },
      data: {
        email: evt.data.email_addresses[0]?.email_address ?? '',
        firstName: evt.data.first_name ?? '',
        lastName: evt.data.last_name ?? '',
        imageUrl: evt.data.image_url ?? '',
      },
    })
  }

  if (eventType === 'user.deleted') {
    await db.user.delete({
      where: { clerkId: evt.data.id },
    })
  }

  return new Response('OK', { status: 200 })
}
```

### 4.2 Install svix for webhook verification
```bash
npm install svix
```

### 4.3 Add CLERK_WEBHOOK_SECRET to ENV.md and .env.example
```
CLERK_WEBHOOK_SECRET=whsec_...
```

### 4.4 Prisma schema additions
```prisma
model User {
  id        String   @id @default(cuid())
  clerkId   String   @unique
  email     String   @unique
  firstName String   @default("")
  lastName  String   @default("")
  imageUrl  String   @default("")
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  // Add your app-specific relations here
  // subscription Subscription?
  // items        Item[]
}
```

Run migration:
```bash
npx prisma migrate dev --name add-users-table
```

---

## Phase 5: Helper utilities

### 5.1 Get DB user from Clerk ID
```typescript
// src/lib/auth.ts
import { auth } from '@clerk/nextjs/server'
import { db } from '@/lib/db'

export async function getCurrentUser() {
  const { userId } = await auth()
  if (!userId) return null

  return db.user.findUnique({
    where: { clerkId: userId }
  })
}

export async function requireUser() {
  const user = await getCurrentUser()
  if (!user) throw new Error('User not found')
  return user
}
```

### 5.2 Typed auth for API routes
```typescript
// src/lib/api-auth.ts
import { auth } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'

export async function withAuth<T>(
  handler: (userId: string) => Promise<T>
): Promise<T | NextResponse> {
  const { userId } = await auth()
  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }
  return handler(userId)
}
```

Usage:
```typescript
export async function GET() {
  return withAuth(async (userId) => {
    const items = await db.items.findMany({ where: { userId } })
    return NextResponse.json(items)
  })
}
```

---

## Phase 6: Verification checklist

Run through every item:

```bash
# Start dev server
npm run dev
```

Manual checks:
- [ ] `/sign-up` renders Clerk sign-up form
- [ ] `/sign-in` renders Clerk sign-in form
- [ ] Create a test account via `/sign-up`
- [ ] After sign-up, redirected to `/dashboard`
- [ ] `/dashboard` accessible when signed in
- [ ] Navigating to `/dashboard` when signed out redirects to `/sign-in`
- [ ] Sign out works and redirects to `/`
- [ ] API route returns 401 when called without auth
- [ ] API route returns data when called with valid session

Webhook check (use Stripe CLI pattern or ngrok):
```bash
# Install Clerk CLI or use ngrok to expose localhost
# Set webhook URL in Clerk dashboard → Webhooks
# Create a test user and verify it appears in your database
```

---

## Phase 7: Update project state

After completing setup:

1. Update `.cc-forge/state.json`:
```json
{
  "current_stage": 7,
  "stage_name": "BILLING",
  "gates_passed": [..., {
    "gate": "auth-complete",
    "date": "[today]",
    "notes": "Clerk setup complete, webhook syncing users to DB"
  }]
}
```

2. Update `ARCHITECTURE.md` with auth flow:
```markdown
## Authentication
Clerk handles all authentication. Users sign in/up via Clerk-hosted
components. A webhook at /api/webhooks/clerk syncs user data to our
PostgreSQL database on user.created, user.updated, user.deleted events.
All protected routes use clerkMiddleware. DB queries always scope to
the authenticated userId — never trust client-supplied user IDs.
```

3. Record in `DECISIONS.md`:
```markdown
## ADR-00X: Use Clerk for authentication
- Decision: Clerk
- Rationale: Best DX, pre-built UI components, generous free tier,
  webhook-based DB sync is clean and reliable
- Alternatives: NextAuth (more setup, more flexibility), Supabase Auth
  (only if using Supabase DB)
```

---

## Common issues

**Middleware not protecting routes:**
Check that `matcher` in middleware config includes your app routes.
The default matcher excludes `_next` and static files — this is correct.

**Webhook verification failing:**
- Confirm `CLERK_WEBHOOK_SECRET` matches the secret in Clerk dashboard
- Confirm the webhook endpoint is in `isPublicRoute` in middleware
- Use Clerk dashboard → Webhooks → test to debug

**User not found in DB after sign-up:**
- Check webhook is registered in Clerk dashboard
- Check webhook logs in Clerk dashboard for delivery failures
- Verify `user.created` is in the subscribed events list

**Session not available in API route:**
Use `await auth()` (async) not `auth()` (sync) in Next.js 14+ App Router.
