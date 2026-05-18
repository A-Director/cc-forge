# Testing Standards

## Philosophy

Test behaviour, not implementation. A refactor that changes no behaviour
should not break any test. If your test breaks because you renamed a function,
the test is testing the wrong thing.

## Stack

- **Unit/integration:** Vitest (not Jest — faster, better ESM support)
- **E2E:** Playwright
- **API testing:** Vitest + supertest or native fetch
- **Test database:** separate DB or in-memory SQLite via Prisma

## Coverage targets

| Layer | Minimum | Target |
|---|---|---|
| Service functions | 80% | 90% |
| API route handlers | 70% | 85% |
| Utility functions | 90% | 100% |
| UI components | 50% | 70% |
| E2E critical flows | all critical paths | — |

Coverage is a floor, not a ceiling. 100% coverage with bad tests is useless.

## What to test

**Always test:**
- Service layer business logic — every significant branch
- API routes — auth check, happy path, error cases
- Data transformations — especially ones that touch money or permissions
- Webhook handlers — every event type you handle

**Usually test:**
- Utility functions with non-trivial logic
- Custom hooks
- Form validation logic

**Skip or minimise:**
- One-line wrappers around libraries
- Pure UI rendering (test interaction, not markup)
- Third-party library behaviour

## Test structure

```typescript
// Arrange → Act → Assert
describe('itemService.create', () => {
  it('creates an item for the authenticated user', async () => {
    // Arrange
    const userId = 'user_123'
    const input = { name: 'Test item', description: 'Test' }

    // Act
    const item = await itemService.create(userId, input)

    // Assert
    expect(item.userId).toBe(userId)
    expect(item.name).toBe(input.name)
  })

  it('throws when userId is missing', async () => {
    await expect(
      itemService.create('', { name: 'Test' })
    ).rejects.toThrow('userId required')
  })
})
```

## Test file location

Co-locate tests with source:
```
src/services/item-service.ts
src/services/item-service.test.ts

src/app/api/items/route.ts
src/app/api/items/route.test.ts
```

E2E tests in a top-level folder:
```
e2e/
  auth.spec.ts
  billing.spec.ts
  core-flow.spec.ts
```

## Naming

- Test files: `*.test.ts` or `*.spec.ts`
- Test descriptions: plain English, describe the behaviour
- `describe` block: the thing being tested
- `it` block: what it should do

```typescript
// Bad
it('test1', () => {})
it('handles the case', () => {})

// Good
describe('getUserSubscription', () => {
  it('returns null when user has no subscription', async () => {})
  it('returns CANCELED status when subscription is deleted', async () => {})
  it('returns false for expired subscription even if status is ACTIVE', async () => {})
})
```

## Mocking

```typescript
// Mock at the module boundary, not deep inside
vi.mock('@/lib/db', () => ({
  db: {
    user: {
      findUnique: vi.fn(),
      create: vi.fn(),
    }
  }
}))

// Reset between tests
beforeEach(() => {
  vi.clearAllMocks()
})
```

Never mock what you're actually testing. If testing `itemService.create`,
mock the database but don't mock `itemService` itself.

## Vitest config

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config'
import path from 'path'

export default defineConfig({
  test: {
    environment: 'node',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules/', '.next/', 'e2e/'],
      thresholds: {
        lines: 70,
        functions: 70,
        branches: 70,
      }
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    }
  }
})
```
