# Installing cc-forge

cc-forge is a framework of markdown files, not a package you install via npm
or pip. Installation means: getting the prerequisites, running the install
script, and scaffolding your first project.

This takes about 10 minutes the first time.

---

## Prerequisites

You need these before anything else. cc-forge won't work without them.

### 1. Claude Code

cc-forge is built entirely around Claude Code (the CLI, not the web app).

```bash
# Verify you have it
claude --version
```

If not installed: https://claude.ai/code

You need an active Claude subscription (Pro or Max) — cc-forge uses Opus
for gate reviews and Sonnet for daily build tasks.

### 2. Node.js 20+

```bash
# Verify version
node --version   # must be 20.x or higher

# Install if needed: https://nodejs.org
# Or via nvm:
nvm install 20
nvm use 20
```

### 3. Git

```bash
git --version
```

If not installed: https://git-scm.com

---

## Step 1 — Clone cc-forge

Clone cc-forge to a permanent location on your machine (not inside a project):

```bash
# Recommended location
cd ~
git clone https://github.com/A-Director/cc-forge.git

# Or anywhere you keep your tools
mkdir -p ~/tools
cd ~/tools
git clone https://github.com/A-Director/cc-forge.git
```

---

## Step 2 — Run the install script

This installs all required Claude Code plugins and MCP servers globally.
Run it once — it applies to all your projects.

```bash
bash ~/cc-forge/scripts/hermes-install.sh
```

**What it installs:**

| Tool | Type | Purpose |
|---|---|---|
| superpowers | Claude Code plugin | Agentic workflow — brainstorm, TDD, subagent execution |
| claude-mem | Claude Code plugin | Session memory across projects |
| task-master-ai | MCP server | Task management — reads your PRD, tracks progress |
| context7 | MCP server | Live library docs injected into sessions |
| criticalthink | Command | Forces Claude to challenge its own assumptions |
| Hermes commands | Commands | /hermes-status, /hermes-next, /hermes-gate, /hermes-deploy |

**Verify installation:**
```bash
# Check plugins
claude plugins list

# Check MCPs
claude mcp list

# Check commands
ls ~/.claude/commands/ | grep hermes
ls ~/.claude/commands/ | grep criticalthink
```

---

## Step 3 — Set up your first project

### New project (starting from scratch)

```bash
# Create your project folder
mkdir my-project
cd my-project
git init

# Run the cc-forge scaffolding script
bash ~/cc-forge/scripts/hermes-init.sh
```

This creates the cc-forge structure in your project:
```
my-project/
├── .cc-forge/           ← project state
├── .claude/commands/    ← hermes commands
├── .github/workflows/   ← doc sync + @claude actions
├── CLAUDE.md            ← standing orders (stub — fill in)
├── PRD.md               ← product requirements (stub — fill in)
├── .env.example         ← environment variables template
└── .gitignore
```

Then open Claude Code and complete the onboarding interview:
```bash
claude
# In Claude Code:
/hermes-init
```

Hermes will interview you about your project, recommend a stack, and
complete the setup — generating a proper CLAUDE.md, PRD, Taskmaster tasks,
and backlog.

### Existing project (already have code)

```bash
cd your-existing-project

# Copy Hermes commands into the project
mkdir -p .claude/commands
cp ~/cc-forge/hermes/commands/*.md .claude/commands/

# Open Claude Code
claude

# In Claude Code:
/hermes-adopt
```

Hermes will read your entire codebase and produce a gap report — no code
changes, assessment only.

---

## Step 4 — Initialise the backlog (optional but recommended)

After init or adopt, initialise the product backlog:

```bash
# In Claude Code:
/hermes-backlog-init
```

This customises the 10-domain backlog catalogue to your specific stack
and project type, and generates a Definition of Done for each domain.

---

## Keeping cc-forge updated

cc-forge updates regularly as Claude Code ships new features. Pull updates:

```bash
cd ~/cc-forge
git pull origin main

# Re-run install if new tools were added
bash scripts/hermes-install.sh
```

To update Hermes commands in an existing project:
```bash
cp ~/cc-forge/hermes/commands/*.md your-project/.claude/commands/
```

---

## Troubleshooting

### `claude: command not found`
Claude Code is not installed. Install from https://claude.ai/code

### `/hermes-init` not found in Claude Code
The commands weren't copied to `.claude/commands/`. Run:
```bash
cp ~/cc-forge/hermes/commands/*.md .claude/commands/
```

### `task-master: command not found`
Taskmaster MCP wasn't installed. Run:
```bash
claude mcp add task-master-ai --scope user -- npx -y task-master-ai@latest
```

### `context7` not resolving library docs
Context7 MCP wasn't installed. Run:
```bash
claude mcp add context7 --scope user -- npx -y @upstash/context7-mcp
```

### Plugin not activating (superpowers, claude-mem)
Plugins require Claude Code to be restarted after installation:
```bash
# Exit and reopen Claude Code
exit
claude
```

### `hermes-install.sh` fails on Windows
The install script is bash — run it in Git Bash or WSL:
```bash
# Git Bash
bash ~/cc-forge/scripts/hermes-install.sh

# WSL
wsl bash /mnt/c/Users/yourname/cc-forge/scripts/hermes-install.sh
```

---

## What you have after installation

```
Global (applies to all projects):
  ~/.claude/commands/criticalthink.md
  ~/.claude/commands/hermes-*.md
  Claude Code plugins: superpowers, claude-mem
  MCPs: task-master-ai, context7

Per project (after hermes-init or hermes-adopt):
  .cc-forge/state.json        project state
  .cc-forge/backlog/          10-domain product backlog
  .claude/commands/           hermes commands (local copy)
  .github/workflows/          doc sync + @claude GitHub Actions
  CLAUDE.md                   standing orders for this project
  PRD.md                      product requirements
  .env.example                environment variable template
  DECISIONS.md                decision log
  RISKS.md                    risk register
```

---

## Next steps

- Read the [CHEATSHEET.md](./CHEATSHEET.md) — what to run and when
- Run `/hermes-status` at the start of every Claude Code session
- Run `/hermes-adopt` on any existing project to get a gap report
- Star the repo if cc-forge is useful — it helps others find it

Questions? Open a [GitHub Discussion](https://github.com/A-Director/cc-forge/discussions).
