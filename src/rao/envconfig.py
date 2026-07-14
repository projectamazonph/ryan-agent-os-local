from __future__ import annotations

from pathlib import Path

from .env import EnvProfile
from .tomlutil import load_toml, quote


class EnvProfileRegistry:
    def __init__(self, secrets_dir: Path):
        self.secrets_dir = secrets_dir
        self.path = secrets_dir / "references.toml"
        self.secrets_dir.mkdir(parents=True, exist_ok=True)

    def list(self) -> list[EnvProfile]:
        data = load_toml(self.path)
        result: list[EnvProfile] = []
        for name, item in data.get("profiles", {}).items():
            location = item.get("location")
            result.append(
                EnvProfile(
                    name=name,
                    provider=item.get("provider", "dotenv"),
                    location=Path(location).expanduser() if location else None,
                    required=tuple(item.get("required", [])),
                )
            )
        return sorted(result, key=lambda profile: profile.name)

    def get(self, name: str) -> EnvProfile:
        for profile in self.list():
            if profile.name == name:
                return profile
        raise KeyError(f"Unknown environment profile: {name}")

    def add(self, profile: EnvProfile) -> None:
        profiles = {item.name: item for item in self.list()}
        profiles[profile.name] = profile
        self._write(profiles)

    def remove(self, name: str) -> None:
        profiles = {item.name: item for item in self.list()}
        if name not in profiles:
            raise KeyError(f"Unknown environment profile: {name}")
        del profiles[name]
        self._write(profiles)

    def _write(self, profiles: dict[str, EnvProfile]) -> None:
        lines = ["# Secret references only. Never store secret values here.\n\n"]
        for name in sorted(profiles):
            profile = profiles[name]
            lines.append(f"[profiles.{quote(name)}]\n")
            lines.append(f"provider = {quote(profile.provider)}\n")
            if profile.location:
                lines.append(f"location = {quote(str(profile.location.expanduser()))}\n")
            required = ", ".join(quote(key) for key in profile.required)
            lines.append(f"required = [{required}]\n\n")
        self.path.write_text("".join(lines), encoding="utf-8")
        try:
            self.path.chmod(0o600)
        except OSError:
            pass
