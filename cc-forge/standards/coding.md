# Coding Standards

Conventions enforced across all cc-forge projects. These are loaded into
CLAUDE.md at init/adopt time — only the project-specific subset that applies.

---

## Naming

| Thing | Convention | Example |
|---|---|---|
| Files | kebab-case | `user-profile.tsx` |
| Directories | kebab-case | `api-routes/` |
| Components | PascalCase | `UserProfile` |
| Functions | camelCase | `getUserById` |
| Variables | camelCase | `currentUser` |
| Constants | SCREAMING_SNAKE | `MAX_RETRY_COUNT` |
| Types/Interfaces | PascalCase | `UserProfile` |
| Hooks | use* prefix | `useCurrentUser` |
| Boolean vars | is/has/can/should prefix | `isLoading`, `hasAccess` |
| Event handlers | handle* prefix | `handleSubmit` |

## TypeScript

- **Strict mode always on** — `tsconfig.json: "strict": true`
- **No `any`** — use `unknown` + type guards, or proper types
- **No `as` casting without a comment explaining why**
- **Prefer `interface` for object shapes, `type` for unions/intersections**
- **Explicit return types on public functions**
- **No non-null assertions (`!`) without a comment**

```typescript
// Bad
const user = getUser() as User
const name = user!.name
function process(data: any) {}

// Good
const user = getUser()
if (!user) throw new Error('User not found')
const name = user.name
function process(data: unknown): string {
  if (typeof data !== 'string') throw new Error('Expected string')
  return data
}
```

## Function design

- **Single responsibility** — one function does one thing
- **Max 50 lines** — if longer, extract helpers
- **Max 4 parameters** — use an options object beyond that
- **Max nesting depth of 3** — use early returns to reduce nesting
- **Pure functions where possible** — easier to test, easier to reason about

```typescript
// Bad — deep nesting, multiple responsibilities
function processOrder(order, user, inventory) {
  if (order) {
    if (user) {
      if (inventory[order.itemId] > 0) {
        // ... 40 more lines
      }
    }
  }
}

// Good — early returns, focused
function processOrder(order: Order, user: User, inventory: Inventory) {
  if (!order) throw new Error('Order required')
  if (!user) throw new Error('User required')
  if (!hasInventory(inventory, order.itemId)) {
    throw new OutOfStockError(order.itemId)
  }
  return createOrderRecord(order, user)
}
```

## Architecture layers (Next.js)

```
Route Handler / Server Component
  ↓ calls
Service (business logic)
  ↓ calls
Database (Prisma queries)
```

**Never skip layers:**
- Route handlers call services, not Prisma directly
- Services contain all business logic
- Components never call Prisma directly
- Database queries never contain business logic

```typescript
// Bad — route handler doing DB directly
export async function POST(req: Request) {
  const { userId } = await auth()
  const data = await req.json()
  const item = await prisma.item.create({ data: { ...data, userId } })
  return NextResponse.json(item)
}

// Good — route handler calls service
export async function POST(req: Request) {
  const { userId } = await auth()
  const data = await req.json()
  const item = await itemService.create(userId, data)
  return NextResponse.json(item)
}
```

## Error handling

- **Never swallow errors silently**
- **Use typed errors for known failure modes**
- **Always include context in error messages**
- **Log errors at the service layer, not the route layer**

```typescript
// Bad
try {
  await doThing()
} catch (e) {
  // nothing
}

// Good
try {
  await doThing()
} catch (error) {
  logger.error('Failed to do thing', { error, context: { userId, itemId } })
  throw new ServiceError('doThing failed', { cause: error })
}
```

## Comments

- **Comment why, not what** — the code shows what, comments explain why
- **No commented-out code in main branch** — use git instead
- **JSDoc on public service functions**
- **TODO format:** `// TODO(username): description` — add to Taskmaster, don't leave orphaned

## File structure (Next.js)

```
src/
  app/                    # Next.js App Router pages and layouts
    (auth)/               # Route group — auth pages
    (dashboard)/          # Route group — protected pages
    api/                  # API routes
  components/             # Reusable React components
    ui/                   # Base UI components (shadcn etc.)
  lib/                    # Utilities, helpers, configs
    db.ts                 # Prisma client singleton
    auth.ts               # Auth helpers
    stripe.ts             # Stripe client
  services/               # Business logic layer
  types/                  # Shared TypeScript types
  hooks/                  # Custom React hooks
```
