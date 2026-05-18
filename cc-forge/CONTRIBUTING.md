# Contributing to cc-forge

cc-forge is an open-core project. The core framework is MIT licensed
and contributions are welcome. This document explains how to contribute
effectively.

---

## What we're looking for

**High-value contributions:**
- New persona definitions (domain-specific: Django, mobile, data pipelines)
- Stage agents for alternative stacks (Supabase auth, Paddle billing, Fly.io deploy)
- Improvements to existing personas with better prompts or coverage
- Bug reports: things that don't work as described
- Doc improvements: clarity, accuracy, missing steps

**Out of scope:**
- UI dashboard (Anthropic's Agent View handles this)
- Integrations with specific editors or IDEs
- Anything that requires a separate hosted service

---

## How to contribute

### Bug reports
Open a GitHub Issue with:
- What you expected to happen
- What actually happened
- Which file/agent/persona was involved
- Your stack (Next.js version, Node version, OS)

### New personas or stage agents
1. Fork the repo
2. Create your file following the existing persona format (see `personas/cto.md`)
3. Test it on a real project — don't submit untested agents
4. Open a PR with:
   - What the persona/agent does
   - What stack or scenario it's designed for
   - An example of the output it produces

### Improvements to existing files
- Open an issue first for significant changes (saves wasted effort)
- Small fixes (typos, broken commands, outdated API) — PR directly

---

## File format standards

All agent and persona files must follow this format:

```markdown
---
name: [kebab-case-name]
description: >
  [What it does, when to use it, what model it uses.
  2-4 sentences. This is what Hermes reads to decide when to invoke it.]
model: [claude-opus-4-6 / claude-sonnet-4-6 / claude-haiku-4-5]
tools: [comma-separated list of Claude Code tools needed]
---

# [Title]

[Role statement — one paragraph describing who this agent is]

---

## [Sections specific to this agent]

## Output format

[The report template this agent produces]
```

Model selection guidance:
- Opus: hard reasoning, security audits, architecture, CEO/CTO reviews
- Sonnet: most personas, standard build tasks
- Haiku: simple checks, cost reports, fast lookups

---

## Prompt quality standards

All prompts in cc-forge must follow `standards/prompt-standards.md`.

Key requirements:
- Positive instructions ("use X") not negative ("don't use Y")
- Specific, not generic — name files, line numbers, exact commands
- XML tags for structured sections
- Coverage-first for review agents (report everything, don't self-filter)
- Role statement at the top of every agent

---

## Testing your contribution

Before submitting a PR:
1. Run the agent/persona on a real project (not a toy example)
2. Verify the output matches the documented output format
3. Check that the prompt follows `standards/prompt-standards.md`
4. Verify model selection is appropriate for the task

---

## Community

GitHub Discussions is the primary channel for:
- Questions about using cc-forge
- Ideas for new features or personas
- Sharing what's working (and what isn't) on real projects

---

## License

By contributing, you agree that your contributions will be licensed
under the same MIT license as the core project.

Premium components (`/hermes status` TUI, pre-built Clerk/Stripe agents)
are maintained separately and are not part of the open-source repo.
