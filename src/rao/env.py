from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import subprocess
from typing import Mapping, Sequence


@dataclass(frozen=True)
class EnvProfile:
    name: str
    provider: str
    location: Path | None
    required: tuple[str, ...]


@dataclass(frozen=True)
class EnvCheckResult:
    profile: str
    present: dict[str, bool]
    source_exists: bool

    @property
    def valid(self) -> bool:
        return self.source_exists and all(self.present.values())

    def render(self) -> str:
        lines = [f"Environment profile: {self.profile}", ""]
        for key, available in self.present.items():
            lines.append(f"{key:<32} {'present' if available else 'missing'}")
        if not self.source_exists:
            lines.extend(["", "Profile source is unavailable."])
        lines.extend(["", "Secret values were not displayed."])
        return "\n".join(lines)


class EnvBroker:
    def load(self, profile: EnvProfile) -> dict[str, str]:
        if profile.provider == "process":
            return dict(os.environ)
        if profile.provider != "dotenv":
            raise ValueError(f"Unsupported environment provider: {profile.provider}")
        if profile.location is None or not profile.location.expanduser().exists():
            return {}
        return parse_dotenv(profile.location.expanduser())

    def check(self, profile: EnvProfile) -> EnvCheckResult:
        values = self.load(profile)
        source_exists = profile.provider == "process" or bool(profile.location and profile.location.expanduser().exists())
        present = {key: bool(values.get(key) or os.environ.get(key)) for key in profile.required}
        return EnvCheckResult(profile=profile.name, present=present, source_exists=source_exists)

    def run(self, profile: EnvProfile, command: Sequence[str], cwd: Path) -> int:
        values = self.load(profile)
        env = dict(os.environ)
        env.update(values)
        completed = subprocess.run(list(command), cwd=cwd, env=env, check=False)
        return completed.returncode


def parse_dotenv(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        result[key] = value
    return result
