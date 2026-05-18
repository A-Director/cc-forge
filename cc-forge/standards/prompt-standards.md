# Prompt Standards

Standards for writing prompts in cc-forge agents, persona definitions, CLAUDE.md
instructions, and any prompt that goes into a Claude Code session or API call.

Sourced from Anthropic's official Claude 4 prompting best practices, distilled
for the cc-forge context.

---

## The golden rule

Before finalising any prompt, ask: *Could a capable colleague follow these
instructions without asking clarifying questions?* If not, the prompt needs work.

---

## 1. Be specific and direct

Claude responds to explicit instructions. Vague prompts produce vague results
and waste tokens on intent-parsing.

**Weak:**
```
Review the code for issues.
```

**Strong:**
```
Review src/api/auth/login.ts for security vulnerabilities. Focus on:
input validation, SQL injection risk, and JWT handling. Report every
issue you find including low-severity ones — a separate step will filter.
For each issue: file + line, what it is, why it matters, how to fix it.
```

The difference is the difference between 2 turns and 8 turns.

---

## 2. Provide context and rationale

Claude generalises from explanations. Telling it *why* a constraint exists
produces better results than just stating the constraint.

**Weak:**
```
Never use console.log.
```

**Strong:**
```
Never use console.log — this is a production codebase and console output
is captured in Railway logs. Use the structured logger at src/lib/logger.ts
instead so log levels and context are preserved.
```

---

## 3. Use XML tags for structure

XML tags help Claude parse complex prompts without ambiguity — especially
when mixing instructions, context, examples, and variable inputs.

```xml
<instructions>
Review the authentication flow described below.
</instructions>

<context>
This is a Next.js 14 app using Clerk for auth. The issue is intermittent
401 errors on valid sessions.
</context>

<code>
// paste relevant code here
</code>

<output_format>
Respond with: diagnosis, root cause, fix, and test to verify.
</output_format>
```

Use consistent, descriptive tag names. Nest tags for hierarchical content.

---

## 4. Use examples (few-shot prompting)

Examples are the most reliable way to steer output format, tone, and
structure. 3–5 well-crafted examples beat lengthy instructions.

- **Relevant:** Mirror your actual use case
- **Diverse:** Cover edge cases and variations
- **Wrapped in `<example>` tags** so Claude distinguishes them from instructions

```xml
<instructions>
Write a task description for Taskmaster.
</instructions>

<examples>
  <example>
    <input>Set up Stripe billing</input>
    <output>
      Implement Stripe billing integration. Install stripe package, create
      products and prices in Stripe dashboard, build /api/billing/checkout
      endpoint that creates a Stripe Checkout session, handle webhook at
      /api/billing/webhook (verify signature), grant/revoke access based on
      subscription status stored in users table. Test with Stripe CLI.
    </output>
  </example>
</examples>
```

---

## 5. Tell Claude what to do, not what not to do

Positive instructions outperform negative ones. Claude follows "do X"
better than "don't do Y."

**Weak:**
```
Don't use markdown in your response.
```

**Strong:**
```
Write your response in clear flowing prose paragraphs. No headers,
no bullet points, no bold text.
```

---

## 6. Match prompt style to desired output

The formatting style of your prompt influences Claude's output style.
If you want plain prose output, write your prompt in plain prose.
If you want structured output, write your prompt with structure.

For cc-forge agent definitions (which produce structured reports):
write agent definitions with the same structure you want in the output.
The report format sections in each persona are examples of this in action.

---

## 7. Effort levels — use them deliberately

The effort parameter lets you tune Claude's intelligence vs. token spend.

In cc-forge context:

| Task | Effort | Model |
|---|---|---|
| Hard architecture decisions | `xhigh` | Opus |
| Security audit, deep review | `xhigh` | Opus |
| Standard feature build | `high` (default) | Sonnet |
| Test writing, refactoring | `high` | Sonnet |
| Simple lookups, quick checks | `low` | Haiku |
| CFO cost report | `low` | Haiku |

If you observe shallow reasoning on complex problems, raise effort to `high` or `xhigh` rather than prompting around it.

Set effort in CLAUDE.md per-project if you have a preference:
```
## Effort
Default to high effort for all tasks unless the task is clearly
a simple lookup or mechanical operation.
```

---

## 8. Long context — structure carefully

When passing large files or documents to Claude:

- **Put long content at the top** of the prompt, above your query.
  Queries at the end can improve response quality by up to 30% in tests, especially with complex, multi-document inputs.
- **Use XML document tags** for multiple files:

```xml
<documents>
  <document index="1">
    <source>src/api/auth/login.ts</source>
    <document_content>
      [file contents here]
    </document_content>
  </document>
</documents>

Review the above file for security vulnerabilities.
```

- **Ask Claude to quote first, then analyse.** For long documents, instruct
  Claude to extract relevant quotes before reasoning about them.

---

## 9. Role prompting

Setting a role in the system prompt focuses Claude's behaviour and tone for your use case. Even a single sentence makes a difference.

Every cc-forge persona definition starts with a role statement:
```
You are a senior security engineer with deep experience in web application
security, OWASP standards, and production incident response.
```

This is not decoration. It shapes every response that follows.
Be specific about experience level, domain, and perspective.

---

## 10. Controlling subagent spawning

Claude Opus 4.7 tends to spawn fewer subagents by default. Give explicit guidance around when subagents are desirable.

For cc-forge gate reviews where you want parallel subagents:
```
Invoke each persona review as a separate subagent with a clean context
window. Do not run all reviews in the same context — each must be
independent to avoid bias from the previous review.
```

For build sessions where you want focused single-agent work:
```
Do not spawn a subagent for work you can complete directly in this
response. Spawn multiple subagents only when fanning out across
independent files or tasks that can run in parallel.
```

---

## 11. Code review prompts — coverage over filtering

Claude Opus 4.7 follows instructions like "be conservative" or "only report high-severity issues" more faithfully than earlier models. This can cause measured recall to fall even though the model's underlying ability has improved.

For cc-forge review agents (Security Auditor, QA, CTO), use this pattern:

```
Report every issue you find, including ones you are uncertain about or
consider low-severity. Do not filter for importance or confidence at this
stage — a separate verification step will handle that. Your goal is
coverage: it is better to surface a finding that later gets filtered out
than to silently drop a real issue. For each finding, include your
confidence level and estimated severity.
```

---

## 12. Verbosity control

Claude Opus 4.7 calibrates response length to how complex it judges the task to be. If your product depends on a certain style or verbosity, you may need to tune prompts.

For cc-forge session start (needs to be brief):
```
Keep your session start summary to under 150 words. The developer is
here to build, not read. One line for last task, one line for next task,
flags only if urgent.
```

For persona reports (needs to be thorough):
```
Be as specific as necessary. Do not truncate findings for brevity.
A complete report that covers everything is more valuable than a
brief one that misses something important.
```

---

## 13. Agentic system prompts — specify upfront, minimise turns

Providing well-specified, clear, and accurate task descriptions upfront can help maximise autonomy and minimise extra token usage. Ambiguous or underspecified prompts conveyed progressively over multiple user turns reduce token efficiency.

For cc-forge agents that run autonomously (adopt, deploy, quality):
- State the full task, intent, and constraints in the first turn
- Include all relevant file paths, scope, and output format
- Do not rely on follow-up turns to clarify intent

Bad pattern:
```
Turn 1: "Review the codebase"
Turn 2: "Focus on security"
Turn 3: "Actually just look at auth"
Turn 4: "And give me a structured report"
```

Good pattern:
```
Turn 1: "Review src/api/auth/ for OWASP Top 10 vulnerabilities.
         Scope: authentication and session management only.
         Output format: structured report with CRITICAL / HIGH / MEDIUM
         / LOW sections, file+line references, and specific fixes."
```

---

## Writing CLAUDE.md instructions

CLAUDE.md is a permanent prompt that loads every session. Every token
costs. Apply all the above standards, plus:

- **Positive instructions only** — "use kebab-case" not "don't use camelCase for files"
- **Specific, not generic** — only write what Claude would get wrong without being told
- **No documentation** — CLAUDE.md is not README. No project history, no feature descriptions
- **No task state** — "currently building auth" does not belong here
- **Under 600 tokens** — audit regularly. Remove anything generic.
- **Test it** — start a fresh session and check if Claude actually follows it

Template:
```markdown
# [Project Name]
[One sentence: what it does]

## Stack
[Exact versions, not approximations]

## Commands
[Exact commands that work in this repo, nothing else]

## Conventions
[Only what Claude would get wrong — specific to this project]

## Key constraints
[Hard rules that must never be violated]
```

---

## Anti-patterns to avoid

| Anti-pattern | Problem | Fix |
|---|---|---|
| `Don't use X` | Negative instruction, less reliable | `Use Y instead of X` |
| Vague scope (`"review the code"`) | Forces Claude to guess | Name the file, function, concern |
| Progressive clarification over turns | Token waste, worse results | Full spec in turn 1 |
| Generic CLAUDE.md | Costs tokens for nothing | Keep only project-specific constraints |
| Same prompt for all models | Opus and Haiku need different effort | Match prompt to model and task |
| Instructions without rationale | Claude can't generalise | Add `because [reason]` |
| Pasting files | Dead weight in context | Use `@filename` references |

---

## 14. Backlog item format standard

All backlog items in cc-forge domain catalogues follow this format.
The standard field references an external authoritative source so
items are defensible, reviewable, and contribution-friendly.

```markdown
### [DOMAIN-NNN] Item title written as an outcome

**Outcome:** What done looks like from the user/operator perspective
**Standard:** [Standard Name — Section/Clause/ID]
**Owner:** [Persona name]
**Blocks:** Stage [N] / Launch / Post-launch / Not blocking
**Applicability:** Universal / Stack: [name] / Optional: [condition]
**Status:** not-started | in-progress | done | not-applicable
**Evidence:** [commit / file:line / URL — filled in when done]
```

**Standard field values:**
- Real standard: `OWASP ASVS 4.0 — V9.2.1`
- cc-forge standard: `cc-forge — [domain] standards`
- Opinionated: `cc-forge — opinionated` (with rationale in Outcome)

**Status flow:**
```
not-started → in-progress → done (with evidence)
                          → not-applicable (with DECISIONS.md entry)
```

**Override rule:**
Any `not-applicable` item MUST have a corresponding entry in `DECISIONS.md`.
Any security, reliability, or compliance item marked `not-applicable` MUST
also have an entry in `RISKS.md`.

Never leave a `not-applicable` item without a paper trail.
