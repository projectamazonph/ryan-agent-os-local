from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shlex
import subprocess
import sys
import threading

from .env import EnvBroker, EnvProfile
from .git import fingerprint
from .guard import RepetitionGuard
from .project import ProjectContract
from .state import StateStore


@dataclass(frozen=True)
class RunResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    blocked: bool = False


class CommandRunner:
    def __init__(self, store: StateStore):
        self.store = store
        self.guard = RepetitionGuard(store)
        self.env_broker = EnvBroker()

    def run_named(
        self,
        root: Path,
        contract: ProjectContract,
        command_name: str,
        env_profile: EnvProfile | None = None,
        force: bool = False,
        stream: bool = True,
    ) -> RunResult:
        if command_name not in contract.commands:
            available = ", ".join(contract.commands) or "none"
            raise KeyError(f"Unknown project command: {command_name}. Available: {available}")
        return self.run_shell(
            root=root,
            workspace_id=contract.workspace_id,
            command=contract.commands[command_name],
            manifest=root / ".agent" / "project.toml",
            env_profile=env_profile,
            force=force,
            stream=stream,
            validation_name=command_name,
        )

    def run_shell(
        self,
        root: Path,
        workspace_id: str,
        command: str,
        manifest: Path | None = None,
        env_profile: EnvProfile | None = None,
        force: bool = False,
        stream: bool = True,
        validation_name: str | None = None,
    ) -> RunResult:
        current_fingerprint = fingerprint(root, manifest)
        decision = self.guard.check(workspace_id, current_fingerprint, command)
        if not decision.allowed and not force:
            return RunResult(command, 79, "", decision.reason, blocked=True)

        env = dict(os.environ)
        if env_profile:
            env.update(self.env_broker.load(env_profile))

        process = subprocess.Popen(
            command,
            cwd=root,
            env=env,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []

        if stream:
            def pump(pipe, destination, collector: list[str]) -> None:
                if pipe is None:
                    return
                for line in iter(pipe.readline, ""):
                    collector.append(line)
                    destination.write(line)
                    destination.flush()
                pipe.close()

            stdout_thread = threading.Thread(
                target=pump, args=(process.stdout, sys.stdout, stdout_parts), daemon=True
            )
            stderr_thread = threading.Thread(
                target=pump, args=(process.stderr, sys.stderr, stderr_parts), daemon=True
            )
            stdout_thread.start()
            stderr_thread.start()
            process.wait()
            stdout_thread.join()
            stderr_thread.join()
            stdout = "".join(stdout_parts)
            stderr = "".join(stderr_parts)
        else:
            stdout, stderr = process.communicate()
        signature = self.guard.record(workspace_id, current_fingerprint, command, process.returncode, stderr)
        if validation_name:
            self.store.record_validation(
                workspace_id,
                current_fingerprint,
                validation_name,
                command,
                process.returncode,
            )
        if process.returncode != 0 and signature:
            self.store.record_failure(
                workspace_id=workspace_id,
                command=command,
                error_signature=signature,
                root_cause=None,
                replacement_action="Change one condition, diagnose the root cause, then rerun. Use --force only intentionally.",
            )
        return RunResult(command, process.returncode, stdout, stderr)
