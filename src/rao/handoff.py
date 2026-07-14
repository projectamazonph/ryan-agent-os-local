from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

from .git import fingerprint, git_state
from .project import ProjectContract


def read_handoff(root: Path) -> dict:
    path = root / ".agent" / "handoff.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_handoff(
    root: Path,
    contract: ProjectContract,
    objective: str,
    status: str,
    next_action: str,
    completed: list[str] | None = None,
    remaining: list[str] | None = None,
    validation: dict[str, str] | None = None,
) -> dict:
    git = git_state(root, contract.remote)
    handoff = {
        "version": 1,
        "project": contract.workspace_id,
        "objective": objective,
        "status": status,
        "completed": completed or [],
        "remaining": remaining or [],
        "files_changed": [line[3:] for line in git.status.splitlines() if len(line) > 3],
        "validation": validation or {},
        "next_action": next_action,
        "fingerprint": {
            "value": fingerprint(root, root / ".agent" / "project.toml"),
            "commit": git.commit,
            "branch": git.branch,
        },
        "updated_at": datetime.now().astimezone().isoformat(),
    }
    path = root / ".agent" / "handoff.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(handoff, indent=2) + "\n", encoding="utf-8")
    _update_current_state(root, objective, next_action, validation or {})
    return handoff


def _update_current_state(root: Path, objective: str, next_action: str, validation: dict[str, str]) -> None:
    lines = [
        f"# Current State: {root.name}",
        "",
        "## Objective",
        "",
        objective,
        "",
        "## Verified State",
        "",
    ]
    if validation:
        for name, status in validation.items():
            lines.append(f"- {name}: {status}")
    else:
        lines.append("- No validation results recorded in this handoff.")
    lines.extend([
        "",
        "## Next Action",
        "",
        next_action,
        "",
        "## Session Notes",
        "",
        f"- Updated: {datetime.now().astimezone().isoformat()}",
    ])
    (root / ".agent" / "current-state.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
