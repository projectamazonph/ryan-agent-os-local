# Agent Integration

## Universal startup block

```text
Before repository work:
1. Run `rao context` from the current directory.
2. Run `rao doctor`.
3. Treat `.agent/project.toml` as the only source for project commands.
4. Read `.agent/known-issues.md` and `.agent/handoff.json`.
5. Continue from the exact next action.
6. Use tests first and make the smallest verified implementation change.
7. Use `rao validate` before declaring completion.
8. Use `rao push` or `rao ship`, never a reconstructed push flow.
9. Write a handoff and close the session before ending.
```

## Hermes

Add the universal startup block to the global Hermes agent instructions. Set an agent identity:

```bash
export RAO_AGENT=hermes
```

Start work:

```bash
rao start amph-academy --objective "Implement enrollment progress tracking"
```

## Claude Code

Add the startup block to the global Claude instructions or repository `CLAUDE.md`. Use:

```bash
export RAO_AGENT=claude-code
rao start amph-academy --objective "Fix the mobile navigation regression"
```

## Codex

Add the startup block to the global agent policy. Use:

```bash
export RAO_AGENT=codex
rao start amph-academy --objective "Add integration tests for course completion"
```

## Cursor and VS Code agents

Put the startup block into the workspace rules. The agent should run `rao context` before broad code search.

## Local LLMs

Expose only these safe commands by default:

```text
rao context
rao doctor
rao run test
rao run lint
rao validate
rao handoff show
rao failures list
```

Reserve `rao commit`, `rao push`, `rao ship`, and `rao env run` for agents with write and execution permission.

## Permission profiles

### Research agent

Allowed:

- `rao context`
- `rao doctor`
- `rao failures list`
- Read repository files

Denied:

- Environment injection
- Commit
- Push
- Deployment

### Coding agent

Allowed:

- Research permissions
- File edits
- `rao run`
- `rao validate`
- Handoff updates

Denied:

- Protected-branch push
- Production deployment

### Release agent

Allowed:

- Coding permissions
- `rao commit`
- `rao push`
- `rao ship`

Require successful validation and a clean feature branch.
