from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

from .detection import DetectedProject, detect_project
from .git import git_state, default_branch, fingerprint
from .paths import RaoPaths
from .registry import Workspace, WorkspaceRegistry
from .tomlutil import dump_project_toml


@dataclass(frozen=True)
class OnboardResult:
    workspace: Workspace
    detected: DetectedProject


def onboard_repository(
    root: Path,
    paths: RaoPaths,
    registry: WorkspaceRegistry,
    workspace_id: str | None = None,
    env_profile: str | None = None,
    force: bool = False,
) -> OnboardResult:
    root = root.expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Repository does not exist: {root}")
    detected = detect_project(root)
    workspace_id = workspace_id or _slug(detected.name)
    git = git_state(root)
    branch = default_branch(root) if git.is_repo else "main"
    agent_dir = root / ".agent"
    project_path = agent_dir / "project.toml"
    if project_path.exists() and not force:
        raise FileExistsError(f"Agent contract already exists: {project_path}. Use --force to regenerate it.")
    agent_dir.mkdir(parents=True, exist_ok=True)
    project_data = {
        "project": detected.name,
        "workspace_id": workspace_id,
        "project_type": detected.project_type,
        "package_manager": detected.package_manager,
        "env_profile": env_profile,
        "commands": detected.commands,
        "remote": "origin",
        "default_branch": branch,
    }
    project_path.write_text(dump_project_toml(project_data), encoding="utf-8")
    _write_if_missing(agent_dir / "current-state.md", _current_state(detected.name))
    _write_if_missing(agent_dir / "known-issues.md", _known_issues())
    _write_if_missing(agent_dir / "decisions.md", _decisions())
    _write_if_missing(agent_dir / "AGENT_INSTRUCTIONS.md", _agent_instructions())
    if not (agent_dir / "handoff.json").exists() or force:
        handoff = {
            "version": 1,
            "project": workspace_id,
            "objective": "Repository onboarded into Ryan Agent OS",
            "status": "ready",
            "completed": ["Workspace registered", "Agent contract generated"],
            "remaining": ["Set the current objective", "Run rao doctor", "Run rao validate"],
            "files_changed": [],
            "validation": {},
            "next_action": "Run `rao start %s --objective \"Describe the task\"`" % workspace_id,
            "updated_at": datetime.now().astimezone().isoformat(),
        }
        (agent_dir / "handoff.json").write_text(json.dumps(handoff, indent=2) + "\n", encoding="utf-8")
        handoff["fingerprint"] = {
            "value": fingerprint(root, project_path),
            "commit": git.commit,
            "branch": git.branch,
        }
        (agent_dir / "handoff.json").write_text(json.dumps(handoff, indent=2) + "\n", encoding="utf-8")
    workspace = registry.register(workspace_id, root, "origin", branch)
    return OnboardResult(workspace=workspace, detected=detected)


def _write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def _slug(value: str) -> str:
    result = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return "-".join(part for part in result.split("-") if part)


def _current_state(name: str) -> str:
    return f"""# Current State: {name}

## Objective

Repository onboarded. Replace this line with the active objective.

## Verified State

- Tests: not run
- Lint: not run
- Typecheck: not run
- Build: not run

## Next Action

Run `rao doctor` and then `rao validate`.

## Session Notes

- Keep this file concise.
- Update facts, not speculation.
"""


def _known_issues() -> str:
    return """# Known Issues and Failed Approaches

Record failures that future agents must not repeat.

## Global Restrictions

- Do not recursively search the full home directory or storage for this repository.
- Do not recursively search for `.env` files.
- Do not repeat an unchanged failed command.
- Do not print secret values.
- Do not force-push protected branches.
"""


def _decisions() -> str:
    return """# Decisions

Record durable technical and workflow decisions here.

| Date | Decision | Rationale | Status |
|---|---|---|---|
| | Use Ryan Agent OS for workspace resolution and safe operations | Prevent repeated discovery and failed flows | Active |
"""


def _agent_instructions() -> str:
    return """# Mandatory Agent Startup Contract

1. Run `rao context` from this repository or `rao context <workspace-id>`.
2. Read `.agent/project.toml` and follow its declared commands.
3. Read `.agent/current-state.md`, `.agent/known-issues.md`, and `.agent/handoff.json`.
4. Run `rao doctor` before changing code.
5. Use Test-Driven Development and Loop Engineering.
6. Use `rao run <command-name>` instead of inventing project commands.
7. Use `rao push` instead of a raw push workflow.
8. Before ending, run `rao handoff write` with the exact next action.

## Hard Restrictions

- Never recursively search the user's entire home directory or mounted storage.
- Never search recursively for secret files.
- Never print secret values.
- Never repeat an unchanged failed command; diagnose and alter one condition first.
- Never push directly to a protected default branch without explicit authorization.
- Never claim validation passed unless Ryan Agent OS recorded a successful run.
"""
