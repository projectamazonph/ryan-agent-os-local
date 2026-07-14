from __future__ import annotations

from pathlib import Path

from .paths import RaoPaths


POLICIES = """# Ryan Agent OS global policies

[execution]
identical_command_retries = 0
similar_command_retries = 2
maximum_debug_loops = 4

[filesystem]
recursive_search_default = "denied"
maximum_search_depth = 4
maximum_files = 5000

[git]
protected_branches = ["main", "master", "production", "release"]
require_validation_before_push = true
require_clean_worktree_before_push = true

[security]
print_secret_values = false
recursive_env_search = false
"""

RECIPES = """# Built-in recipes are executed by `rao recipe run <name>`.

[recipes.start]
description = "Run doctor, open a session, and print authoritative context."
steps = ["doctor", "session-open", "context"]

[recipes.baseline]
description = "Run declared test, lint, typecheck, and build commands."
steps = ["validate"]

[recipes.safe-push]
description = "Validate, enforce branch/worktree policy, and push the current branch."
steps = ["validate", "push"]

[recipes.finish]
description = "Write a structured handoff and close the active session."
steps = ["handoff", "session-close"]
"""

GLOBAL_AGENT_POLICY = """# Ryan Agent OS: Global Agent Policy

## Mandatory startup

1. Resolve repositories with `rao resolve` or `rao context`; never search full storage.
2. Run `rao doctor` before implementation.
3. Read the generated context and repository `.agent/` contract.
4. Use declared commands through `rao run`.
5. Use Test-Driven Development and Loop Engineering.
6. Use `rao push`; do not rebuild the authentication and validation flow manually.
7. End with `rao handoff write` and an exact next action.

## Prohibited behavior

- Recursive whole-home or whole-storage workspace searches.
- Recursive searches for `.env` or secret files.
- Printing or copying secret values into logs, prompts, handoffs, or documentation.
- Repeating an unchanged failed command against the same repository fingerprint.
- Inventing package-manager, build, deployment, or Git procedures when a project command exists.
- Force-pushing protected branches.
"""


def initialize_global_files(paths: RaoPaths) -> list[Path]:
    paths.ensure()
    created: list[Path] = []
    files = {
        paths.config / "policies.toml": POLICIES,
        paths.config / "recipes.toml": RECIPES,
        paths.config / "AGENT_POLICY.md": GLOBAL_AGENT_POLICY,
        paths.config / "workspaces.toml": "# Managed by Ryan Agent OS.\n",
        paths.secrets / "references.toml": "# Secret references only. Never store secret values here.\n",
    }
    for path, content in files.items():
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            created.append(path)
    try:
        (paths.secrets / "references.toml").chmod(0o600)
    except OSError:
        pass
    return created
