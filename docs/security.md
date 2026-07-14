# Security Model

## Secret handling

Ryan Agent OS stores only:

- Environment profile name
- Provider type
- Secret-file location
- Required variable names

It does not store environment values in TOML, SQLite, handoffs, or logs.

`rao env check` reports only presence. `rao env run` injects values into the child process environment.

## Commit guard

`rao commit` and `rao ship` inspect staged filenames and block common secret material, including:

- `.env` and `.env.*`
- SSH private keys
- PEM, P12, PFX, and key files
- Common credential and service-account files
- Secret configuration files

The check is defensive, not a replacement for a dedicated secret scanner.

## Filesystem boundaries

Repository discovery requires an explicit root and bounded depth. Hidden directories and common dependency/cache directories are skipped.

## Git safety

- Protected branches are blocked by default.
- Detached HEAD pushes are blocked.
- Dirty worktrees are blocked before push.
- Managed pre-push hooks validate even when raw `git push` is attempted.
- Existing unmanaged hooks are preserved by default.
