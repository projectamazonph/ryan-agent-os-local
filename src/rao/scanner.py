from __future__ import annotations

from pathlib import Path


def find_git_repositories(root: Path, max_depth: int = 3, max_repositories: int = 100) -> list[Path]:
    root = root.expanduser().resolve()
    found: list[Path] = []
    denied_names = {"node_modules", ".venv", "venv", ".cache", ".local", "Library", "$RECYCLE.BIN"}

    def walk(path: Path, depth: int) -> None:
        if len(found) >= max_repositories or depth > max_depth:
            return
        if (path / ".git").exists():
            found.append(path)
            return
        try:
            children = list(path.iterdir())
        except (PermissionError, OSError):
            return
        for child in children:
            if len(found) >= max_repositories:
                break
            if child.is_dir() and child.name not in denied_names and not child.name.startswith("."):
                walk(child, depth + 1)

    walk(root, 0)
    return found
