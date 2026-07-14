# Ryan Agent OS 0.1.0

This release provides the working local control-plane core for persistent coding-agent operations.

## Verified scenarios

- Installed without network access or third-party runtime packages.
- Created and onboarded fresh Node and Python repositories.
- Generated passing baseline tests for new repositories.
- Registered and resolved workspace paths without full-storage search.
- Attached and checked environment profiles without printing values.
- Blocked staged `.env` files while allowing `.env.example`.
- Blocked identical failed commands against unchanged repository state.
- Validated, committed, and pushed a feature branch to a clean remote.
- Preserved a clean worktree after managed post-commit hooks.
- Recorded validation and Git events in SQLite.

## Scope

Version 0.1.0 is the authoritative CLI and persistence core. MCP and graphical interfaces are planned after the operational contracts remain stable in real use.
