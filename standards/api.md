# API Standards

Conventions for all API routes in cc-forge projects.

---

## URL structure

```
GET    /api/[resource]           list
POST   /api/[resource]           create
GET    /api/[resource]/[id]      get one
PATCH  /api/[resource]/[id]      partial update
DELETE /api/[resource]/[id]      delete
POST   /api/[resource]/[id]/[action]  specific action
```

Examples:
```
GET    /api/items
POST   /api/items
GET    /api/items/123
PATCH  /api/items/123
DELETE /api/items/123
POST   /api/items/123/archive
```

## Response envelope

All responses use a consistent structure:

```typescript
// Success
{ data: T, meta?: { page, total, hasMore } }

// Error
{ error: string, code?: string, details?: unknown }
```

```typescript
// src/lib/api-response.ts
import { NextResponse } from 'next/server'

export function ok<T>(data: T, status = 200) {
  return NextResponse.json({ data }, { status })
}

export function created<T>(data: T) {
  return NextResponse.json({ data }, { status: 201 })
}

export function badRequest(error: string, details?: unknown) {
  return NextResponse.json({ error, details }, { status: 400 })
}

export function unauthorized() {
  return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
}

export function forbidden() {
  return NextResponse.json({ error: 'Forbidden' }, { status: 403 })
}

export function notFound(resource = 'Resource') {
  return NextResponse.json({ error: `${resource} not found` }, { status: 404 })
}

export function serverError(error?: string) {
  return NextResponse.json(
    { error: error ?? 'Internal server error' },
    { status: 500 }
  )
}
```

## HTTP status codes

| Code | When to use |
|---|---|
| 200 | Successful GET, PATCH, DELETE |
| 201 | Successful POST (resource created) |
| 400 | Validation error, bad request |
| 401 | Not authenticated |
| 403 | Authenticated but not authorised |
| 404 | Resource not found |
| 409 | Conflict (duplicate, state mismatch) |
| 422 | Validation passed but business rule failed |
| 500 | Unexpected server error |

## Rate limiting

Add rate limiting to auth and sensitive endpoints:

```typescript
// Use Upstash Redis + @upstash/ratelimit for production
// Or a simple in-memory limiter for early-stage apps
```

## API route template

```typescript
import { auth } from '@clerk/nextjs/server'
import { NextRequest } from 'next/server'
import { z } from 'zod'
import { ok, created, badRequest, unauthorized, notFound } from '@/lib/api-response'
import { itemService } from '@/services/item-service'

const createSchema = z.object({
  name: z.string().min(1).max(100),
})

export async function GET() {
  const { userId } = await auth()
  if (!userId) return unauthorized()

  const items = await itemService.list(userId)
  return ok(items)
}

export async function POST(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) return unauthorized()

  const body = await req.json()
  const result = createSchema.safeParse(body)
  if (!result.success) return badRequest('Validation failed', result.error.flatten())

  const item = await itemService.create(userId, result.data)
  return created(item)
}
```

---
