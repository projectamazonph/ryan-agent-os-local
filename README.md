# Ryan Agent OS

Ryan Agent OS (`rao`) is a lightweight local control plane that stops coding agents from rediscovering your machine, repeating failed commands, hunting for environment keys, and rebuilding Git workflows in every session.

It uses only the Python 3.11+ standard library at runtime:

- TOML for stable configuration
- SQLite for sessions, failures, command outcomes, and validation history
- Repository-local `.agent/` contracts for durable project truth
- Git hooks and guarded commands for safe automation

## What it fixes

| Repeated agent failure | Ryan Agent OS behavior |
|---|---|
| Searches the entire disk for a repository | Resolves a registered workspace immediately |
| Hunts recursively for `.env` files | Loads a named secret reference without displaying values |
| Repeats the same failed command | Blocks the unchanged command against the same repository fingerprint |
| Invents install, test, build, and push commands | Uses `.agent/project.toml` as the executable contract |
| Starts every session with no context | Generates one compact context brief and structured handoff |
| Pushes without tests or targets the wrong branch | Validates, checks branch policy, checks worktree state, then pushes |
| Accidentally stages secrets | Blocks likely secret files before commit |

## Installation

### Linux, macOS, WSL, or Termux

```bash
./scripts/install.sh
```

For Termux:

```bash
./scripts/install-termux.sh
```

### Windows PowerShell

```powershell
Set-ExecutionPolicy -Scope Process Bypass
./scripts/install.ps1
```

The installer copies the standard-library-only application into a user-local directory and adds the `rao` launcher under the user-local binary directory. It does not need network access or third-party packages.


### Optional shell shortcuts

```bash
source /path/to/ryan-agent-os/scripts/shell-functions.sh
cproj amph-academy
rstart amph-academy "Fix progress synchronization" hermes
rship amph-academy "fix: synchronize progress"
```

## First-time setup

```bash
rao init
```

Default control-plane location:

```text
~/.ryan-agent-os/
├── config/
│   ├── workspaces.toml
│   ├── policies.toml
│   ├── recipes.toml
│   └── AGENT_POLICY.md
├── state/
│   ├── agent-os.db
│   ├── sessions/
│   ├── logs/
│   └── locks/
└── secrets/
    └── references.toml
```

Override it with `RAO_HOME`:

```bash
export RAO_HOME="$HOME/.config/ryan-agent-os"
```

## Create a new repository

```bash
rao new my-app --template node
cd my-app
rao start my-app --agent hermes --objective "Build the authentication flow"
```

Available templates:

- `generic`
- `node`
- `python`

`rao new` performs the following:

1. Creates the directory.
2. Initializes Git with a `main` branch.
3. Creates basic project files.
4. Detects the runtime and package manager.
5. Generates the `.agent/` contract.
6. Registers the workspace.
7. Installs managed Git hooks.

## Onboard an existing repository

```bash
cd /path/to/repository
rao onboard . --id amph-academy
rao doctor amph-academy
rao context amph-academy
```

For a controlled migration of repositories under one known root:

```bash
rao scan ~/workspaces --depth 2 --register
```

This is a bounded search. It does not scan the entire home directory or mounted storage.

## Daily workflow

```bash
rao start amph-academy \
  --agent codex \
  --objective "Add course progress synchronization"

rao run test amph-academy
rao run lint amph-academy
rao validate amph-academy

rao handoff write amph-academy \
  --objective "Add course progress synchronization" \
  --status paused \
  --completed "Added the failing concurrency test" \
  --remaining "Implement optimistic locking" \
  --next "Implement the smallest change that passes the new test"

rao session close amph-academy \
  --status paused \
  --next "Implement optimistic locking"
```

## One-command commit and delivery

Create a feature branch first:

```bash
git switch -c feature/progress-sync
```

Validate and commit staged changes:

```bash
rao commit amph-academy -m "feat: synchronize course progress"
```

Validate, stage all changes, commit, and push:

```bash
rao ship amph-academy \
  --all \
  -m "feat: synchronize course progress"
```

`rao ship` will stop when:

- A declared validation command fails
- The branch is protected
- The worktree remains dirty after the commit
- A likely secret file is staged
- Git has no current branch
- The push fails

## Environment profiles

Store secret values in your preferred private dotenv file. Ryan Agent OS stores only the file reference and required variable names.

```bash
rao env add amph-academy-env \
  --file ~/.config/ryan-secrets/amph-academy.env \
  --required DATABASE_URL \
  --required AUTH_SECRET \
  --required OPENAI_API_KEY

rao env attach amph-academy amph-academy-env
rao env check amph-academy
rao env run amph-academy -- npm run migrate
```

Output reports only `present` or `missing`. Values are never printed by the environment broker.

## Commands

| Command | Purpose |
|---|---|
| `rao init` | Initialize global configuration and state |
| `rao new` | Create and onboard a new repository |
| `rao onboard` | Register an existing repository |
| `rao refresh` | Redetect package manager and project commands |
| `rao projects` | List registered repositories |
| `rao resolve` | Return the authoritative repository path |
| `rao context` | Generate the compact session brief |
| `rao doctor` | Validate tools, Git, commands, auth, and environment |
| `rao start` | Run doctor, open a session, and print context |
| `rao run` | Execute a declared project command |
| `rao validate` | Run test, lint, typecheck, and build in order |
| `rao commit` | Validate and create an intentional commit |
| `rao push` | Validate and push the current branch |
| `rao ship` | Validate, commit, and push |
| `rao hooks` | Install managed Git hooks |
| `rao env` | Register, attach, check, and inject environments |
| `rao failures` | Inspect or add negative operational memory |
| `rao session` | Open, inspect, and close work sessions |
| `rao handoff` | Read or write structured continuity state |
| `rao recipe` | Run built-in deterministic workflows |
| `rao scan` | Discover repositories under one explicit bounded root |

## Repository contract

Every onboarded repository receives:

```text
.agent/
├── project.toml
├── AGENT_INSTRUCTIONS.md
├── current-state.md
├── known-issues.md
├── decisions.md
└── handoff.json
```

Example `.agent/project.toml`:

```toml
project = "amph-academy"
workspace_id = "amph-academy"
project_type = "node"
package_manager = "pnpm"
env_profile = "amph-academy-env"

[commands]
install = "pnpm install"
test = "pnpm test"
lint = "pnpm lint"
typecheck = "pnpm typecheck"
build = "pnpm build"

[git]
remote = "origin"
default_branch = "main"

[workflow]
tests_before_implementation = true
require_clean_build_before_push = true
methodologies = ["test-driven-development", "loop-engineering"]
```

Edit this file when the repository needs a command the detector cannot infer.

## Repetition guard

A command execution is identified by:

- Workspace ID
- Exact command
- Current commit and branch
- Staged and unstaged Git diffs
- Untracked file contents up to the safety limit
- Lockfile contents
- Agent contract contents

When the exact command already failed against the same fingerprint, Ryan Agent OS blocks it. Change the code, configuration, environment, or command before retrying. `--force` exists for deliberate exceptions.

## Git hooks

Managed hooks provide:

- `pre-push`: protected-branch enforcement and validation
- `post-commit`: records the new repository fingerprint in the handoff
- `post-checkout`: prints the authoritative context command

Existing unmanaged hooks are preserved unless `--force` is explicitly used.

## Agent startup instruction

Place this in Hermes, Claude Code, Codex, Cursor, or another coding agent's global instructions:

```text
At the beginning of repository work, run `rao context` from the current repository.
Treat the returned path, commands, environment status, failures, and next action as authoritative.
Run `rao doctor` before implementation.
Use `rao run <name>` for project commands, `rao validate` before completion, and `rao push` or `rao ship` for delivery.
Never recursively search full storage or search recursively for secret files.
Before ending, write a structured handoff and close the active Ryan Agent OS session.
```

See [`docs/agent-integration.md`](docs/agent-integration.md) for complete integration patterns.

## Development

```bash
python -m unittest discover -s tests -v
python -m compileall -q src
```

The project follows Test-Driven Development and Loop Engineering. See [`AGENTS.md`](AGENTS.md).
