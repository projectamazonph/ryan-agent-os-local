from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import sys
import shlex

from .env import EnvBroker, EnvProfile
from .git import gh_auth_ok, git_state
from .project import ProjectContract
from .registry import Workspace


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    blocking: bool = True


def run_doctor(workspace: Workspace, contract: ProjectContract, env_profile: EnvProfile | None) -> list[Check]:
    root = workspace.path
    git = git_state(root, contract.remote)
    checks = [
        Check("Workspace path", root.exists(), str(root)),
        Check("Agent contract", (root / ".agent" / "project.toml").exists(), str(root / ".agent" / "project.toml")),
        Check("Git repository", git.is_repo, "available" if git.is_repo else "not initialized"),
        Check("Current branch", bool(git.branch), git.branch or "detached HEAD"),
        Check("Python", sys.version_info >= (3, 11), sys.version.split()[0]),
        Check("Git executable", bool(shutil.which("git")), shutil.which("git") or "missing"),
    ]
    if contract.package_manager:
        executable = {
            "python": sys.executable,
            "maven": "mvn",
            "gradle": "gradle",
        }.get(contract.package_manager, contract.package_manager)
        checks.append(Check("Package manager", bool(shutil.which(executable) or Path(executable).exists()), executable))
    if git.remote_url and "github.com" in git.remote_url:
        ok, detail = gh_auth_ok(root)
        checks.append(Check("GitHub authentication", ok, detail, blocking=False))
    if env_profile:
        env_check = EnvBroker().check(env_profile)
        missing = [key for key, available in env_check.present.items() if not available]
        checks.append(
            Check(
                "Environment profile",
                env_check.valid,
                "valid" if env_check.valid else "missing: " + ", ".join(missing),
            )
        )
    for name, command in contract.commands.items():
        executable = _command_executable(command)
        available = bool(executable and (shutil.which(executable) or (root / executable).exists()))
        checks.append(Check(f"Command `{name}`", available, command))
    return checks


def render_checks(checks: list[Check]) -> str:
    lines = ["RYAN AGENT OS DOCTOR", "=" * 56]
    for check in checks:
        marker = "PASS" if check.ok else ("WARN" if not check.blocking else "FAIL")
        lines.append(f"[{marker}] {check.name}: {check.detail}")
    blocking_failures = [check for check in checks if not check.ok and check.blocking]
    lines.extend(["", f"Blocking failures: {len(blocking_failures)}"])
    return "\n".join(lines)


def _command_executable(command: str) -> str | None:
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
    for part in parts:
        if "=" in part and not part.startswith(("./", "/")):
            key, _, _ = part.partition("=")
            if key.replace("_", "").isalnum():
                continue
        return part
    return None
