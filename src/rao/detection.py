from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class DetectedProject:
    name: str
    project_type: str
    package_manager: str | None
    commands: dict[str, str]


def detect_project(root: Path) -> DetectedProject:
    root = root.expanduser().resolve()
    if (root / "package.json").exists():
        return _detect_node(root)
    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        return _detect_python(root)
    if (root / "Cargo.toml").exists():
        return DetectedProject(
            name=_toml_project_name(root / "Cargo.toml", ("package", "name")) or root.name,
            project_type="rust",
            package_manager="cargo",
            commands={"test": "cargo test", "lint": "cargo clippy --all-targets --all-features", "build": "cargo build"},
        )
    if (root / "go.mod").exists():
        return DetectedProject(
            name=root.name,
            project_type="go",
            package_manager="go",
            commands={"test": "go test ./...", "lint": "go vet ./...", "build": "go build ./..."},
        )
    if (root / "pom.xml").exists():
        return DetectedProject(
            name=root.name,
            project_type="java-maven",
            package_manager="maven",
            commands={"test": "mvn test", "build": "mvn package"},
        )
    if (root / "gradlew").exists() or (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        wrapper = "./gradlew" if (root / "gradlew").exists() else "gradle"
        return DetectedProject(
            name=root.name,
            project_type="java-gradle",
            package_manager="gradle",
            commands={"test": f"{wrapper} test", "build": f"{wrapper} build"},
        )
    return DetectedProject(name=root.name, project_type="generic", package_manager=None, commands={})


def _detect_node(root: Path) -> DetectedProject:
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    manager = "npm"
    if (root / "pnpm-lock.yaml").exists():
        manager = "pnpm"
    elif (root / "yarn.lock").exists():
        manager = "yarn"
    elif (root / "bun.lockb").exists() or (root / "bun.lock").exists():
        manager = "bun"
    scripts = package.get("scripts", {})
    commands: dict[str, str] = {}
    for name in ("install", "dev", "test", "lint", "typecheck", "build", "format"):
        if name == "install":
            continue
        if name in scripts:
            commands[name] = f"{manager} {name}" if manager in {"npm", "pnpm", "yarn", "bun"} else f"{manager} run {name}"
    commands = {"install": f"{manager} install", **commands}
    return DetectedProject(
        name=package.get("name") or root.name,
        project_type="node",
        package_manager=manager,
        commands=commands,
    )


def _detect_python(root: Path) -> DetectedProject:
    name = root.name
    content = ""
    if (root / "pyproject.toml").exists():
        name = _toml_project_name(root / "pyproject.toml", ("project", "name")) or name
        content = (root / "pyproject.toml").read_text(encoding="utf-8", errors="ignore").lower()
    commands: dict[str, str] = {}
    if "pytest" in content or (root / "pytest.ini").exists() or (root / "conftest.py").exists():
        commands["test"] = "python -m pytest"
    elif (root / "tests").exists():
        commands["test"] = "python -m unittest discover -s tests"
    if "ruff" in content or (root / "ruff.toml").exists():
        commands["lint"] = "python -m ruff check ."
    if "mypy" in content or (root / "mypy.ini").exists():
        commands["typecheck"] = "python -m mypy ."
    return DetectedProject(name=name, project_type="python", package_manager="python", commands=commands)


def _toml_project_name(path: Path, keys: tuple[str, str]) -> str | None:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
        return data.get(keys[0], {}).get(keys[1])
    except (OSError, tomllib.TOMLDecodeError):
        return None
