from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

from .env import EnvBroker, EnvProfile
from .git import fingerprint, git_state
from .project import ProjectContract
from .registry import Workspace
from .state import StateStore


def render_context(
    workspace: Workspace,
    contract: ProjectContract,
    store: StateStore,
    env_profile: EnvProfile | None = None,
) -> str:
    root = workspace.path
    git = git_state(root, contract.remote)
    active = store.active_session(workspace.workspace_id)
    latest = store.latest_session(workspace.workspace_id)
    failures = store.list_failures(workspace.workspace_id)[:5]
    handoff = _load_json(root / ".agent" / "handoff.json")
    state_excerpt = _extract_sections(root / ".agent" / "current-state.md")
    current_fingerprint = fingerprint(root, root / ".agent" / "project.toml")
    stored_fingerprint = handoff.get("fingerprint", {}).get("value")
    handoff_status = "unknown" if not stored_fingerprint else ("current" if stored_fingerprint == current_fingerprint else "stale")
    validations = store.latest_validations(workspace.workspace_id, current_fingerprint)
    env_status = "not configured"
    if env_profile:
        check = EnvBroker().check(env_profile)
        env_status = "valid" if check.valid else "missing requirements"

    lines = [
        "RYAN AGENT OS CONTEXT",
        "=" * 56,
        f"PROJECT             {contract.project}",
        f"WORKSPACE ID        {workspace.workspace_id}",
        f"PATH                {root}",
        f"TYPE                {contract.project_type}",
        f"PACKAGE MANAGER     {contract.package_manager or 'not declared'}",
        f"BRANCH              {git.branch or 'not available'}",
        f"COMMIT              {(git.commit or 'not available')[:12]}",
        f"WORKTREE            {'clean' if git.clean else _status_summary(git.status)}",
        f"REMOTE              {git.remote_url or 'not configured'}",
        f"ENVIRONMENT         {env_status}",
        f"FINGERPRINT         {current_fingerprint}",
        f"HANDOFF STATUS      {handoff_status}",
        "",
        "CURRENT OBJECTIVE",
        (active or {}).get("objective") or state_excerpt.get("Objective") or handoff.get("objective") or (latest or {}).get("objective") or "Not recorded",
        "",
        "NEXT VERIFIED ACTION",
        state_excerpt.get("Next Action") or handoff.get("next_action") or (latest or {}).get("next_action") or "Run `rao doctor`.",
        "",
        "DECLARED COMMANDS",
    ]
    if contract.commands:
        for name, command in contract.commands.items():
            lines.append(f"  {name:<14} {command}")
    else:
        lines.append("  No commands declared. Edit .agent/project.toml.")

    lines.extend(["", "LAST VALIDATION"])
    if validations:
        for name, item in validations.items():
            lines.append(f"  {name:<14} {'passed' if item['exit_code'] == 0 else 'failed'} at {item['created_at']}")
    else:
        lines.append("  No validation recorded for the current fingerprint.")

    lines.extend(["", "DO NOT REPEAT"])
    known = _known_issue_bullets(root / ".agent" / "known-issues.md")
    for item in known[:5]:
        lines.append(f"  - {item}")
    for failure in failures:
        replacement = failure.get("replacement_action") or "Diagnose before retrying."
        lines.append(f"  - `{failure['command']}` failed: {replacement}")
    if not known and not failures:
        lines.append("  - No recorded project-specific failures.")

    lines.extend([
        "",
        "MANDATORY METHOD",
        "  Test-Driven Development; Loop Engineering; smallest verified change.",
        "",
        "SAFE ENTRYPOINTS",
        f"  rao doctor {workspace.workspace_id}",
        f"  rao validate {workspace.workspace_id}",
        f"  rao push {workspace.workspace_id}",
    ])
    return "\n".join(lines)


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _extract_sections(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif current:
            sections[current].append(line)
    result: dict[str, str] = {}
    for name, values in sections.items():
        text = "\n".join(values).strip()
        if text:
            result[name] = text
    return result


def _known_issue_bullets(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [line[2:].strip() for line in lines if line.startswith("- ")]


def _status_summary(status: str) -> str:
    lines = [line for line in status.splitlines() if line.strip()]
    return f"{len(lines)} changed path{'s' if len(lines) != 1 else ''}"
