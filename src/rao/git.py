from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import shutil
import subprocess


@dataclass(frozen=True)
class GitState:
    is_repo: bool
    branch: str | None
    commit: str | None
    status: str
    remote_url: str | None

    @property
    def clean(self) -> bool:
        return not self.status.strip()


def git_state(root: Path, remote: str = "origin") -> GitState:
    if not (root / ".git").exists() and _run(root, ["git", "rev-parse", "--is-inside-work-tree"]).returncode != 0:
        return GitState(False, None, None, "", None)
    branch = _stdout(root, ["git", "branch", "--show-current"]) or None
    commit = _stdout(root, ["git", "rev-parse", "HEAD"]) or None
    status = _stdout(root, ["git", "status", "--porcelain"], strip=False)
    remote_url = _stdout(root, ["git", "remote", "get-url", remote]) or None
    return GitState(True, branch, commit, status, remote_url)


def fingerprint(root: Path, project_manifest: Path | None = None) -> str:
    state = git_state(root)
    lockfiles = [
        "pnpm-lock.yaml", "package-lock.json", "yarn.lock", "bun.lock", "bun.lockb",
        "poetry.lock", "uv.lock", "Pipfile.lock", "Cargo.lock", "go.sum",
    ]
    digest = hashlib.sha256()
    for value in (state.commit or "no-commit", state.branch or "detached", state.status):
        digest.update(value.encode("utf-8"))
    if state.is_repo:
        exclusions = [
            ":(exclude).agent/handoff.json",
            ":(exclude).agent/current-state.md",
        ]
        for args in (
            ["git", "diff", "--binary", "--", ".", *exclusions],
            ["git", "diff", "--cached", "--binary", "--", ".", *exclusions],
        ):
            result = _run(root, list(args))
            digest.update(result.stdout.encode("utf-8"))
        untracked = _stdout(root, ["git", "ls-files", "--others", "--exclude-standard"]).splitlines()
        for relative in sorted(untracked)[:500]:
            if relative in {".agent/handoff.json", ".agent/current-state.md"}:
                continue
            path = root / relative
            digest.update(relative.encode("utf-8"))
            try:
                if path.is_file() and path.stat().st_size <= 1_000_000:
                    digest.update(path.read_bytes())
            except OSError:
                pass
    for name in lockfiles:
        path = root / name
        if path.exists() and path.is_file():
            digest.update(name.encode("utf-8"))
            digest.update(path.read_bytes())
    if project_manifest and project_manifest.exists():
        digest.update(project_manifest.read_bytes())
    return digest.hexdigest()[:20]


def current_branch(root: Path) -> str | None:
    return git_state(root).branch


def init_repo(root: Path, default_branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(["git", "init", "-b", default_branch], cwd=root, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        fallback = subprocess.run(["git", "init"], cwd=root, check=False, capture_output=True, text=True)
        if fallback.returncode != 0:
            raise RuntimeError(fallback.stderr.strip() or "Unable to initialize Git repository")
        subprocess.run(["git", "checkout", "-b", default_branch], cwd=root, check=False, capture_output=True, text=True)


def gh_auth_ok(root: Path) -> tuple[bool, str]:
    if not shutil.which("gh"):
        return False, "GitHub CLI is not installed; Git push may still work through Git credentials."
    result = subprocess.run(["gh", "auth", "status"], cwd=root, check=False, capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output


def _stdout(root: Path, args: list[str], strip: bool = True) -> str:
    result = _run(root, args)
    if result.returncode != 0:
        return ""
    value = result.stdout
    return value.strip() if strip else value


def _run(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=root, check=False, capture_output=True, text=True)


SENSITIVE_PATTERNS = (
    ".env", ".env.", "id_rsa", "id_ed25519", ".pem", ".p12", ".pfx",
    "credentials.json", "service-account", ".key", "secrets.toml", "secrets.yaml",
)


def sensitive_staged_files(root: Path) -> list[str]:
    result = _run(root, ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    if result.returncode != 0:
        return []
    found: list[str] = []
    for raw in result.stdout.splitlines():
        path = raw.strip()
        lower = path.lower()
        name = Path(lower).name
        safe_example = name.endswith((".example", ".sample", ".template"))
        if not safe_example and (name == ".env" or name.startswith(".env.") or any(pattern in lower for pattern in SENSITIVE_PATTERNS[2:])):
            found.append(path)
    return found


def default_branch(root: Path, remote: str = "origin") -> str:
    remote_head = _stdout(root, ["git", "symbolic-ref", f"refs/remotes/{remote}/HEAD", "--short"])
    if remote_head and "/" in remote_head:
        return remote_head.split("/", 1)[1]
    state = git_state(root, remote)
    if state.branch in {"main", "master"}:
        return state.branch
    for candidate in ("main", "master"):
        result = _run(root, ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{candidate}"])
        if result.returncode == 0:
            return candidate
    return "main"
