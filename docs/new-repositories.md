# New Repository Automation

## Recommended command

```bash
rao new interview-lab-v2 --template node
```

This removes the gap between `git init` and agent readiness.

## Existing `git init` habit

When a repository was created outside Ryan Agent OS:

```bash
cd new-repository
rao onboard .
```

## Refresh after choosing a stack

A generic repository may later become Node, Python, Rust, Go, Maven, or Gradle. Redetect it with:

```bash
rao refresh
```

The refresh preserves:

- Workspace ID
- Environment profile
- Git remote name
- Default branch

It updates:

- Project type
- Package manager
- Detected commands

## Team bootstrap file

Commit `.agent/` to the repository. Do not commit global state or secret references.

Recommended committed files:

```text
.agent/project.toml
.agent/AGENT_INSTRUCTIONS.md
.agent/current-state.md
.agent/known-issues.md
.agent/decisions.md
.agent/handoff.json
```
