# Architecture

## Components

```text
Agent or human
      │
      ▼
rao CLI
├── Workspace registry
├── Project detector
├── Repository contract loader
├── Environment broker
├── Repetition guard
├── Validation runner
├── Git safety layer
├── Session and handoff manager
└── Bounded repository scanner
      │
      ├── TOML configuration
      ├── SQLite operational state
      └── Repository .agent/ contract
```

## Configuration versus state

### Configuration

Stable declarations live in TOML:

- Workspace paths
- Project commands
- Environment references
- Policies
- Recipes

### Operational state

Frequently changing facts live in SQLite:

- Sessions
- Known failures
- Command executions
- Validation outcomes

### Repository continuity

Project-specific facts live under `.agent/` and travel with the repository:

- Current objective
- Known failed approaches
- Durable decisions
- Exact next action
- Git fingerprint

## Trust boundaries

Ryan Agent OS treats these as authoritative:

1. The workspace registry for repository location
2. `.agent/project.toml` for executable commands
3. The environment profile registry for secret locations
4. Git for branch and worktree state
5. SQLite for previous command outcomes
6. `.agent/handoff.json` for continuity

It does not infer secret locations, scan full storage, or invent project commands after onboarding.

## Fingerprinting

The repetition guard hashes:

- Commit
- Branch
- Porcelain worktree status
- Staged and unstaged binary diffs
- Bounded untracked file content
- Known lockfiles
- `.agent/project.toml`

This lets an agent retry after a real change without allowing a pointless identical loop.
