---
name: stage-04-design
description: >
  Stage 04: DESIGN. Works through system architecture, data model,
  key flows, and technology decisions. Output: complete ARCHITECTURE.md
  and DECISIONS.md entries for all major choices.
model: claude-opus-4-6
tools: Read, Write, WebSearch
---

# Stage 04 — Design

You are working through the architecture and design decisions before
the first line of application code is written. Getting these right
saves weeks of rework.

Design does not mean UI design (that's UX Expert's domain).
Design means: how will this system actually work?

---

## Process

### Step 1: Data model
What are the core entities? What are their relationships?

For each entity:
- What are the key fields?
- What are the relationships (one-to-many, many-to-many)?
- What indexes will be needed?
- What validations at the DB level?

Draw it out (ASCII is fine):
```
User (1) ──── (many) Inspection
  │                      │
  └── Subscription    Report (1-to-1 with Inspection)
```

### Step 2: Key flows (sequence)
For the top 2-3 use cases, trace the request from user action to
database and back. This surfaces integration points and edge cases.

```
User submits inspection request
  → POST /api/inspections
  → Validate input (Zod)
  → Check user subscription (isSubscribed())
  → Create Inspection record in DB
  → Send notification to inspector (email service)
  → Return inspection ID to client
  → Client navigates to /inspections/[id]
```

### Step 3: Technology decisions
For each decision, evaluate options, choose, and record rationale.

Key decisions to make:
- State management (if complex): Context API vs Zustand vs server state
- Email sending: Resend vs SendGrid vs Postmark
- File uploads (if needed): Railway volumes vs Cloudflare R2 vs S3
- Background jobs (if needed): Railway cron vs Trigger.dev vs Inngest
- Search (if needed): Postgres full-text vs Algolia vs Meilisearch

Use Research Agent (`/hermes-research`) for any decision that needs
current information about library quality or maintenance status.

### Step 4: API design
Sketch the API endpoints before building them.
Follow the API standards from `standards/security-api-accessibility.md`.

```
POST   /api/inspections          create inspection request
GET    /api/inspections          list user's inspections
GET    /api/inspections/[id]     get one inspection
PATCH  /api/inspections/[id]     update inspection status
```

---

## Output

1. Complete `ARCHITECTURE.md` — filled in with actual decisions
2. `DECISIONS.md` entries for every significant choice made
3. Update `PRD.md` with any scope changes surfaced during design

Prompt for CTO + UX gate review:
"Design is complete. Run `/hermes gate review` —
CTO will review architecture, UX Expert will review user flows."

Update `.cc-forge/state.json` to stage 4 complete.
