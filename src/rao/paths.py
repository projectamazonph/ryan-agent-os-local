from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class RaoPaths:
    root: Path
    config: Path
    state: Path
    sessions: Path
    logs: Path
    locks: Path
    secrets: Path
    database: Path

    @classmethod
    def default(cls) -> "RaoPaths":
        override = os.environ.get("RAO_HOME")
        root = Path(override).expanduser() if override else Path.home() / ".ryan-agent-os"
        return cls.from_root(root)

    @classmethod
    def from_home(cls, home: Path) -> "RaoPaths":
        return cls.from_root(home / ".ryan-agent-os")

    @classmethod
    def from_root(cls, root: Path) -> "RaoPaths":
        root = root.expanduser().resolve()
        state = root / "state"
        return cls(
            root=root,
            config=root / "config",
            state=state,
            sessions=state / "sessions",
            logs=state / "logs",
            locks=state / "locks",
            secrets=root / "secrets",
            database=state / "agent-os.db",
        )

    def ensure(self) -> None:
        for path in (
            self.root,
            self.config,
            self.state,
            self.sessions,
            self.logs,
            self.locks,
            self.secrets,
        ):
            path.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.root, 0o700)
            os.chmod(self.secrets, 0o700)
        except OSError:
            pass
