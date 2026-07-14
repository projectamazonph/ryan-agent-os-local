from __future__ import annotations

from pathlib import Path

from .registry import Workspace, WorkspaceRegistry


def resolve_workspace(registry: WorkspaceRegistry, identifier: str | None, cwd: Path | None = None) -> Workspace:
    if identifier:
        return registry.resolve(identifier)
    cwd = (cwd or Path.cwd()).resolve()
    workspace = registry.find_for_path(cwd)
    if workspace:
        return workspace
    raise KeyError(f"Current directory is not inside a registered workspace: {cwd}. Run `rao onboard .`.")
