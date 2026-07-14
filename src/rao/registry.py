from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .tomlutil import load_toml, write_workspace_registry


@dataclass(frozen=True)
class Workspace:
    workspace_id: str
    path: Path
    remote: str = "origin"
    default_branch: str = "main"


class WorkspaceRegistry:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.path = config_dir / "workspaces.toml"
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _items(self) -> dict[str, dict]:
        data = load_toml(self.path)
        return dict(data.get("workspaces", {}))

    def register(
        self,
        workspace_id: str,
        path: Path,
        remote: str = "origin",
        default_branch: str = "main",
    ) -> Workspace:
        workspace_id = _normalize_id(workspace_id)
        resolved = path.expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Workspace path does not exist: {resolved}")
        items = self._items()
        items[workspace_id] = {
            "path": str(resolved),
            "remote": remote,
            "default_branch": default_branch,
        }
        write_workspace_registry(self.path, items)
        return Workspace(workspace_id, resolved, remote, default_branch)

    def unregister(self, workspace_id: str) -> None:
        items = self._items()
        if workspace_id not in items:
            raise KeyError(f"Unknown workspace: {workspace_id}")
        del items[workspace_id]
        write_workspace_registry(self.path, items)

    def list(self) -> list[Workspace]:
        result = []
        for workspace_id, item in self._items().items():
            result.append(
                Workspace(
                    workspace_id=workspace_id,
                    path=Path(item["path"]).expanduser().resolve(),
                    remote=item.get("remote", "origin"),
                    default_branch=item.get("default_branch", "main"),
                )
            )
        return sorted(result, key=lambda item: item.workspace_id)

    def resolve(self, identifier: str | Path) -> Workspace:
        raw = str(identifier)
        items = self._items()
        if raw in items:
            item = items[raw]
            return Workspace(
                workspace_id=raw,
                path=Path(item["path"]).expanduser().resolve(),
                remote=item.get("remote", "origin"),
                default_branch=item.get("default_branch", "main"),
            )

        candidate = Path(raw).expanduser()
        if candidate.exists():
            resolved = candidate.resolve()
            for workspace_id, item in items.items():
                if Path(item["path"]).expanduser().resolve() == resolved:
                    return Workspace(
                        workspace_id=workspace_id,
                        path=resolved,
                        remote=item.get("remote", "origin"),
                        default_branch=item.get("default_branch", "main"),
                    )
            raise KeyError(f"Path is not registered: {resolved}. Run `rao onboard {resolved}`.")

        raise KeyError(f"Unknown workspace: {raw}")

    def find_for_path(self, path: Path) -> Workspace | None:
        resolved = path.expanduser().resolve()
        for workspace in self.list():
            try:
                resolved.relative_to(workspace.path)
                return workspace
            except ValueError:
                continue
        return None


def _normalize_id(value: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    normalized = "-".join(part for part in normalized.split("-") if part)
    if not normalized:
        raise ValueError("Workspace id cannot be empty")
    return normalized
