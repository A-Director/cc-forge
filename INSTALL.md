# Installing cc-forge

cc-forge ships as a **single-plugin Claude Code marketplace** — not an npm or pip package. Installing means: get the prerequisites, add the plugin, then bootstrap your first project. About 10 minutes the first time.

> New here? Read the [README](./README.md) for what cc-forge is, then come back. The day-to-day commands live in [CHEATSHEET.md](./CHEATSHEET.md).

---

## Prerequisites

| Tool | Check | Get it |
|---|---|---|
| **Claude Code** (CLI, Pro or Max plan) | `claude --version` | https://claude.ai/code |
| **Node.js 20+** | `node --version` | https://nodejs.org (or `nvm install 20`) |
| **Git** | `git --version` | https://git-scm.com |

cc-forge uses Opus for gate reviews and Sonnet for daily build, so an active Claude subscription is required.

---

## Step 1 — Clone cc-forge

Clone to a permanent location (not inside a project):

```bash
git clone https://github.com/A-Director/cc-forge.git ~/cc-forge
```

You can keep it anywhere (`~/tools/cc-forge`, etc.) — just somewhere stable, since the plugin marketplace points at this path.

---

## Step 2 — Install the plugin (inside Claude Code)

cc-forge is a single-plugin marketplace. Open Claude Code and run:

```
/plugin marketplace add ~/cc-forge
/plugin install cc-forge@cc-forge
```

That's the whole install. The plugin system handles **everything** that used to be manual:

- all `/hermes-*` commands,
- hook registration — `SessionStart`, `Stop`, `PreCompact`, `UserPromptSubmit`,
- personas, standards, and the backlog catalogue,
- version management (via `/plugin update`).

> There is no separate global-install shell step. The old `scripts/hermes-install.sh` is now a thin redirect to `/plugin install`.

**Companion plugins (optional but recommended):**

```
/plugin install claude-mem      # session memory across projects
/plugin install superpowers      # agentic workflow — brainstorm, TDD, subagents
```

Restart Claude Code after installing plugins for them to activate.

**Claude Code CLI v2.1.x and earlier — known upstream bug.** Directory-marketplace plugins can install but not auto-add to `enabledPlugins` ([anthropics/claude-code#17832](https://github.com/anthropics/claude-code/issues/17832)). If `/plugin list` shows cc-forge as *disabled* right after install, add it manually to `~/.claude/settings.json`:

```json
"enabledPlugins": {
  "cc-forge@cc-forge": true
}
```

Recent CLI versions auto-enable correctly (verified clean on v2.1.161).

---

## Step 3 — Bootstrap your project

`hermes-bootstrap.sh` creates the project-local state cc-forge needs. It is **idempotent** — safe to re-run.

```bash
cd ~/your-project
bash ~/cc-forge/scripts/hermes-bootstrap.sh
```

It creates `.cc-forge/state.json`, `.cc-forge/usage.log`, the `status/` directory, and updates `.gitignore` with the cc-forge artifact rules (regeneratable views like `status/dashboard.html` ignored; durable records like `status/argus-last-run.md` and `.cc-forge/usage.log` committed).

---

## Step 4 — Onboard

Open Claude Code in your project (`claude`), then:

**New project (greenfield):**
```
/hermes-init
```
Hermes interviews you about the project, recommends a stack, and completes setup — a proper `CLAUDE.md`, PRD stub, Taskmaster tasks, and backlog.

**Existing project:**
```
/hermes-adopt
```
Hermes reads your entire codebase (code, docs, git history) and produces a gap report — assessment only, no code changes.

Then initialise the backlog (recommended):
```
/hermes-backlog-init
```
This customises the 10-domain catalogue to your stack and generates a Definition of Done per domain.

---

## Step 5 — Verify

```
/hermes-argus
```

Argus runs the framework self-check. A healthy install reports **Layer 1 (plugin)** and **Layer 2 (project state)** as `HEALTHY` (or `DEGRADED` if the backlog isn't initialised yet — that's fine). If Argus reports **`CANNOT_LOCATE`** or **Layer 1 failures**, the plugin isn't reachable: confirm `/plugin list` shows `cc-forge@cc-forge` as enabled and that `${CLAUDE_PLUGIN_ROOT}` resolves.

---

## Keeping cc-forge updated

**The easy way — inside any project:**
```
/hermes-update
```
Delegates to `/plugin update`, runs any pending `state.json` migrations, verifies layer reachability via `/hermes-argus`, and reports. Safe to run anytime.

**Manual:**
```bash
cd ~/cc-forge && git pull origin main
# then, in Claude Code:
/plugin update cc-forge@cc-forge
```

**What updates vs. what's never touched:**

| Updated | Never touched |
|---|---|
| `/hermes-*` commands, hooks | `.cc-forge/backlog/` (your backlog) |
| personas, standards | `.cc-forge/state.json` (project state) |
| backlog catalogue (reference) | `CLAUDE.md`, `DECISIONS.md`, `RISKS.md` |

---

## Troubleshooting

**`claude: command not found`** — Claude Code isn't installed: https://claude.ai/code

**`/hermes-*` commands missing after install** — the plugin didn't enable. Check `/plugin list`; if cc-forge shows disabled, see the v2.1.x bug note in Step 2.

**Argus reports `CANNOT_LOCATE`** — the plugin root can't be found. Confirm the plugin is enabled and re-run `/hermes-argus`. (Argus self-discovers its root, so this almost always means the plugin itself isn't installed/enabled.)

**Companion plugin not activating (superpowers, claude-mem)** — restart Claude Code after installing:
```bash
exit
claude
```

**Windows** — the bootstrap script is bash; run it in Git Bash or WSL:
```bash
bash ~/cc-forge/scripts/hermes-bootstrap.sh          # Git Bash
wsl bash /mnt/c/Users/you/cc-forge/scripts/hermes-bootstrap.sh   # WSL
```

---

## What you have after installation

```
Claude Code (global):
  Plugin: cc-forge@cc-forge   → all /hermes-* commands + hooks + personas + standards
  Optional plugins: claude-mem, superpowers

Per project (after bootstrap + init/adopt):
  .cc-forge/state.json        project state
  .cc-forge/usage.log         session event log (committed)
  .cc-forge/backlog/          10-domain product backlog
  status/                     dashboard.html (ignored) · argus-last-run.md (committed)
  CLAUDE.md                   standing orders for this project
  PRD.md · DECISIONS.md · RISKS.md · .env.example
```

---

## Next steps

- Read **[CHEATSHEET.md](./CHEATSHEET.md)** — what to run and when.
- Run `/hermes-status` at the start of every session.
- Run `/hermes-adopt` on any existing project to get a gap report.
- Star the repo if cc-forge is useful — it helps others find it.

Questions? Open a [GitHub Discussion](https://github.com/A-Director/cc-forge/discussions).
