# Git Standards

## Branching

```
main          ← production, always deployable
  └── feat/description    ← new features
  └── fix/description     ← bug fixes
  └── chore/description   ← maintenance, deps, config
  └── docs/description    ← documentation only
  └── hotfix/description  ← urgent production fixes
```

- Branch from `main`, PR back to `main`
- No long-lived branches — merge or delete within one sprint
- Branch names: lowercase, hyphen-separated, under 50 chars

## Commit messages

Format: `type(scope): description`

```
feat(auth): add Clerk webhook for user sync
fix(billing): handle subscription.deleted webhook
chore(deps): upgrade stripe to 14.x
docs(api): add endpoint documentation for /api/users
refactor(services): extract user service from route handlers
test(billing): add webhook handler unit tests
```

Types: `feat` `fix` `chore` `docs` `refactor` `test` `style` `perf`

Rules:
- Lowercase description
- Present tense ("add" not "added")
- Under 72 characters
- Reference task ID when applicable: `feat(auth): add webhook sync [#12]`
- Never commit directly to `main`

## Pull requests

Title: same format as commit message
Description must include:
- What changed and why (not just what)
- How to test it
- Screenshots for UI changes
- `Closes #[task-id]` if resolving a Taskmaster task

PR size: aim for under 400 lines changed. Large PRs get missed issues.
Split large features into sequential PRs (schema → service → route → UI).

## What never goes in Git

```gitignore
.env
.env.local
.env.*.local
node_modules/
.next/
*.log
.DS_Store
.cc-forge/state.json   # state is local, not shared
```

Secrets committed to git are compromised — rotation is required immediately.
