from __future__ import annotations

from pathlib import Path

from .detection import detect_project
from .project import ProjectContract
from .tomlutil import dump_project_toml


def refresh_contract(root: Path) -> ProjectContract:
    existing = ProjectContract.load(root)
    detected = detect_project(root)
    data = {
        "project": detected.name or existing.project,
        "workspace_id": existing.workspace_id,
        "project_type": detected.project_type,
        "package_manager": detected.package_manager,
        "env_profile": existing.env_profile,
        "commands": detected.commands,
        "remote": existing.remote,
        "default_branch": existing.default_branch,
    }
    (root / ".agent" / "project.toml").write_text(dump_project_toml(data), encoding="utf-8")
    return ProjectContract.load(root)
