from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .tomlutil import load_toml


@dataclass(frozen=True)
class Policies:
    protected_branches: frozenset[str]
    require_validation_before_push: bool
    require_clean_worktree_before_push: bool
    identical_command_retries: int
    maximum_debug_loops: int


def load_policies(config_dir: Path) -> Policies:
    data = load_toml(config_dir / "policies.toml")
    git = data.get("git", {})
    execution = data.get("execution", {})
    return Policies(
        protected_branches=frozenset(git.get("protected_branches", ["main", "master", "production", "release"])),
        require_validation_before_push=bool(git.get("require_validation_before_push", True)),
        require_clean_worktree_before_push=bool(git.get("require_clean_worktree_before_push", True)),
        identical_command_retries=int(execution.get("identical_command_retries", 0)),
        maximum_debug_loops=int(execution.get("maximum_debug_loops", 4)),
    )
