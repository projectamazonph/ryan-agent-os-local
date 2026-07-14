# Troubleshooting

## `rao` is not found

Ensure the local binary directory is on `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Current directory is not registered

```bash
rao onboard .
```

## Project commands are wrong or incomplete

```bash
rao refresh
```

Then edit `.agent/project.toml` when detection cannot infer a custom command.

## Environment profile is missing

```bash
rao env add project-env --file /private/path/project.env --required API_KEY
rao env attach project-id project-env
rao env check project-id
```

## An unchanged command is blocked

Inspect negative memory:

```bash
rao failures list
```

Change one material condition before retrying:

- Code
- Configuration
- Environment
- Dependency lockfile
- Exact command

Use `--force` only when rerunning the identical operation is deliberate.

## Push is blocked on `main`

Create a feature branch:

```bash
git switch -c feature/my-change
rao push
```

For an intentional protected-branch push:

```bash
rao push --allow-protected
```

## Existing Git hooks were not replaced

Ryan Agent OS preserves unmanaged hooks. Review them, merge the RAO call manually, or use:

```bash
rao hooks --force
```
