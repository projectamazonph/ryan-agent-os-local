from __future__ import annotations

from dataclasses import dataclass
import hashlib

from .state import StateStore


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    reason: str


class RepetitionGuard:
    def __init__(self, store: StateStore):
        self.store = store

    def check(self, workspace_id: str, fingerprint: str, command: str) -> GuardDecision:
        latest = self.store.latest_command_run(workspace_id, fingerprint, command)
        if latest and latest["exit_code"] != 0:
            return GuardDecision(
                False,
                "This unchanged command previously failed against the same repository fingerprint. "
                "Change the conditions, use a replacement action, or pass --force intentionally.",
            )
        return GuardDecision(True, "No identical failed execution found.")

    def record(self, workspace_id: str, fingerprint: str, command: str, exit_code: int, stderr: str) -> str | None:
        signature = make_error_signature(exit_code, stderr) if exit_code else None
        self.store.record_command_run(workspace_id, fingerprint, command, exit_code, signature)
        return signature


def make_error_signature(exit_code: int, stderr: str) -> str:
    normalized = " ".join(stderr.strip().split())[-2000:]
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    return f"exit:{exit_code}:{digest}"
