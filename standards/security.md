# Security Standards

Core security rules. Enforced by the Security Auditor persona at every
pre-deploy gate. Non-negotiable.

---

## Authentication and authorisation

- **Always use Clerk middleware** — never roll your own auth
- **Server-side auth checks on every protected route and API handler**
- **Never trust client-supplied user IDs** — always use the ID from `auth()`
- **Scope all DB queries to the authenticated user** — `where: { userId }`
- **Check permissions server-side** — not just in the UI

```typescript
// Bad — trusting client-supplied userId
const items = await db.items.findMany({
  where: { userId: req.body.userId }
})

// Good — using server-verified userId
const { userId } = await auth()
const items = await db.items.findMany({
  where: { userId }
})
```

## Secrets management

- **All secrets in environment variables** — never in code or config files
- **`.env.local` in `.gitignore`** — check this before every commit
- **Rotate immediately if a secret is committed** — no exceptions
- **Different secrets for dev/staging/prod** — never share keys across environments
- **Use Railway's environment variable management** — not `.env` files in production

## Input validation

- **Validate at the API boundary** — every route handler
- **Use Zod for schema validation** — consistent, type-safe
- **Validate type, format, length, and range**
- **Return 400 with clear error messages** on validation failure

```typescript
import { z } from 'zod'

const createItemSchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().max(500).optional(),
  price: z.number().positive().max(999999),
})

export async function POST(req: Request) {
  const body = await req.json()
  const result = createItemSchema.safeParse(body)

  if (!result.success) {
    return NextResponse.json(
      { error: 'Validation failed', details: result.error.flatten() },
      { status: 400 }
    )
  }

  // result.data is now typed and validated
}
```

## Webhook verification

Every webhook must verify its signature before processing:

```typescript
// Stripe webhooks
const event = stripe.webhooks.constructEvent(body, signature, secret)

// Clerk webhooks
const evt = wh.verify(body, headers) as WebhookEvent
```

Never process a webhook without signature verification.

## Database

- **Use Prisma ORM** — parameterized queries prevent SQL injection
- **Never use raw SQL with user input**
- **Validate foreign keys** — don't assume a referenced record belongs to the user
- **Soft deletes for user data** — add `deletedAt` rather than hard-deleting

## Error messages

- **Never expose stack traces to users**
- **Generic error messages to users, specific logs internally**
- **Log with context** — userId, route, timestamp

```typescript
// Bad
return NextResponse.json({ error: error.message }, { status: 500 })

// Good
logger.error('Item creation failed', { error, userId, input })
return NextResponse.json(
  { error: 'Something went wrong. Please try again.' },
  { status: 500 }
)
```

## CORS

In production, never use `Access-Control-Allow-Origin: *`.
Configure allowed origins explicitly in Railway or Next.js config.

## Dependencies

- Run `npm audit` before every deploy
- Update dependencies with known CVEs immediately
- Pin dependencies to specific versions in `package.json`

---
