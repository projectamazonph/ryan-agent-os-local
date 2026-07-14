from __future__ import annotations

from pathlib import Path
import tomllib


def load_toml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle)


def quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def write_workspace_registry(path: Path, workspaces: dict[str, dict]) -> None:
    lines = ["# Managed by Ryan Agent OS.\n"]
    for workspace_id in sorted(workspaces):
        item = workspaces[workspace_id]
        lines.append(f"[workspaces.{quote(workspace_id)}]\n")
        lines.append(f"path = {quote(str(item['path']))}\n")
        lines.append(f"remote = {quote(str(item.get('remote', 'origin')))}\n")
        lines.append(f"default_branch = {quote(str(item.get('default_branch', 'main')))}\n")
        lines.append("\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines), encoding="utf-8")


def dump_project_toml(data: dict) -> str:
    lines: list[str] = []
    lines.append(f"project = {quote(data['project'])}\n")
    lines.append(f"workspace_id = {quote(data['workspace_id'])}\n")
    lines.append(f"project_type = {quote(data['project_type'])}\n")
    if data.get("package_manager"):
        lines.append(f"package_manager = {quote(data['package_manager'])}\n")
    if data.get("env_profile"):
        lines.append(f"env_profile = {quote(data['env_profile'])}\n")
    lines.append("\n[commands]\n")
    for name, command in data.get("commands", {}).items():
        lines.append(f"{name} = {quote(command)}\n")
    lines.append("\n[git]\n")
    lines.append(f"remote = {quote(data.get('remote', 'origin'))}\n")
    lines.append(f"default_branch = {quote(data.get('default_branch', 'main'))}\n")
    lines.append("\n[workflow]\n")
    lines.append("tests_before_implementation = true\n")
    lines.append("require_clean_build_before_push = true\n")
    lines.append("methodologies = [\"test-driven-development\", \"loop-engineering\"]\n")
    lines.append("\n[limits]\n")
    lines.append("identical_command_retries = 0\n")
    lines.append("similar_command_retries = 2\n")
    lines.append("maximum_debug_loops = 4\n")
    lines.append("\n[filesystem]\n")
    lines.append("recursive_search_default = \"denied\"\n")
    lines.append("maximum_search_depth = 4\n")
    lines.append("maximum_files = 5000\n")
    return "".join(lines)
