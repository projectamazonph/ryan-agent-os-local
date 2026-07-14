from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .tomlutil import load_toml, dump_project_toml


@dataclass(frozen=True)
class ProjectContract:
    project: str
    workspace_id: str
    project_type: str
    package_manager: str | None
    env_profile: str | None
    commands: dict[str, str]
    remote: str
    default_branch: str
    raw: dict[str, Any]

    @classmethod
    def load(cls, root: Path) -> "ProjectContract":
        path = root / ".agent" / "project.toml"
        if not path.exists():
            raise FileNotFoundError(f"Missing agent contract: {path}. Run `rao onboard {root}`.")
        data = load_toml(path)
        return cls(
            project=data.get("project", root.name),
            workspace_id=data.get("workspace_id", root.name),
            project_type=data.get("project_type", "generic"),
            package_manager=data.get("package_manager"),
            env_profile=data.get("env_profile"),
            commands=dict(data.get("commands", {})),
            remote=data.get("git", {}).get("remote", "origin"),
            default_branch=data.get("git", {}).get("default_branch", "main"),
            raw=data,
        )


def set_env_profile(root: Path, profile_name: str | None) -> ProjectContract:
    contract = ProjectContract.load(root)
    data = {
        "project": contract.project,
        "workspace_id": contract.workspace_id,
        "project_type": contract.project_type,
        "package_manager": contract.package_manager,
        "env_profile": profile_name,
        "commands": contract.commands,
        "remote": contract.remote,
        "default_branch": contract.default_branch,
    }
    (root / ".agent" / "project.toml").write_text(dump_project_toml(data), encoding="utf-8")
    return ProjectContract.load(root)
