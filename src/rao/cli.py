from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import os
import shlex
import subprocess
import sys
from typing import Callable

from . import __version__
from .context import render_context
from .defaults import initialize_global_files
from .doctor import render_checks, run_doctor
from .env import EnvBroker, EnvProfile
from .envconfig import EnvProfileRegistry
from .git import fingerprint, gh_auth_ok, git_state, sensitive_staged_files
from .handoff import read_handoff, write_handoff
from .hooks import install_hooks
from .onboard import onboard_repository
from .paths import RaoPaths
from .policies import load_policies
from .project import ProjectContract, set_env_profile
from .refresh import refresh_contract
from .registry import WorkspaceRegistry
from .resolver import resolve_workspace
from .runner import CommandRunner
from .scanner import find_git_repositories
from .scaffold import create_repository
from .state import StateStore


VALIDATION_ORDER = ("test", "lint", "typecheck", "build")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rao", description="Ryan Agent OS local control plane")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize the global control-plane directories and policies")

    p_new = sub.add_parser("new", help="Create, initialize, onboard, and register a new repository")
    p_new.add_argument("name")
    p_new.add_argument("--path")
    p_new.add_argument("--template", choices=("generic", "node", "python"), default="generic")
    p_new.add_argument("--id")
    p_new.add_argument("--branch", default="main")
    p_new.add_argument("--hooks", action=argparse.BooleanOptionalAction, default=True)

    p_onboard = sub.add_parser("onboard", help="Onboard an existing repository")
    p_onboard.add_argument("path", nargs="?", default=".")
    p_onboard.add_argument("--id")
    p_onboard.add_argument("--env-profile")
    p_onboard.add_argument("--force", action="store_true")
    p_onboard.add_argument("--hooks", action=argparse.BooleanOptionalAction, default=True)

    p_refresh = sub.add_parser("refresh", help="Redetect project commands without losing workspace identity")
    p_refresh.add_argument("workspace", nargs="?")

    sub.add_parser("projects", help="List registered repositories")

    p_resolve = sub.add_parser("resolve", help="Print an authoritative repository path")
    p_resolve.add_argument("workspace", nargs="?")

    p_context = sub.add_parser("context", help="Generate a compact authoritative session brief")
    p_context.add_argument("workspace", nargs="?")

    p_doctor = sub.add_parser("doctor", help="Check repository, tools, Git, auth, and environment")
    p_doctor.add_argument("workspace", nargs="?")

    p_start = sub.add_parser("start", help="Run doctor, open a session, and print context")
    p_start.add_argument("workspace", nargs="?")
    p_start.add_argument("--agent", default=os.environ.get("RAO_AGENT", "unknown-agent"))
    p_start.add_argument("--objective", required=True)

    p_run = sub.add_parser("run", help="Run a command declared in .agent/project.toml")
    p_run.add_argument("command_name")
    p_run.add_argument("workspace", nargs="?")
    p_run.add_argument("--force", action="store_true")

    p_validate = sub.add_parser("validate", help="Run declared checks in deterministic order")
    p_validate.add_argument("workspace", nargs="?")
    p_validate.add_argument("--force", action="store_true")

    p_push = sub.add_parser("push", help="Validate and safely push the current branch")
    p_push.add_argument("workspace", nargs="?")
    p_push.add_argument("--skip-validation", action="store_true")
    p_push.add_argument("--allow-dirty", action="store_true")
    p_push.add_argument("--allow-protected", action="store_true")
    p_push.add_argument("--force-run", action="store_true", help="Allow rerunning previously failed validation commands")

    p_commit = sub.add_parser("commit", help="Validate and create an intentional Git commit")
    p_commit.add_argument("workspace", nargs="?")
    p_commit.add_argument("--message", "-m", required=True)
    p_commit.add_argument("--all", action="store_true", help="Stage all changes after validation")
    p_commit.add_argument("--skip-validation", action="store_true")
    p_commit.add_argument("--allow-sensitive", action="store_true")
    p_commit.add_argument("--force-run", action="store_true")

    p_ship = sub.add_parser("ship", help="Validate, commit, and push a feature branch")
    p_ship.add_argument("workspace", nargs="?")
    p_ship.add_argument("--message", "-m", required=True)
    p_ship.add_argument("--all", action="store_true", help="Stage all changes after validation")
    p_ship.add_argument("--allow-sensitive", action="store_true")
    p_ship.add_argument("--allow-protected", action="store_true")
    p_ship.add_argument("--force-run", action="store_true")

    p_hooks = sub.add_parser("hooks", help="Install managed Git hooks")
    p_hooks.add_argument("workspace", nargs="?")
    p_hooks.add_argument("--force", action="store_true")

    p_hook = sub.add_parser("hook", help=argparse.SUPPRESS)
    p_hook.add_argument("hook_name", choices=("pre-push", "post-commit", "post-checkout"))

    p_scan = sub.add_parser("scan", help="Bounded repository discovery under one explicit root")
    p_scan.add_argument("root")
    p_scan.add_argument("--depth", type=int, default=3)
    p_scan.add_argument("--register", action="store_true")

    p_env = sub.add_parser("env", help="Manage secret references and inject environments")
    env_sub = p_env.add_subparsers(dest="env_command", required=True)
    p_env_add = env_sub.add_parser("add", help="Register a dotenv file reference")
    p_env_add.add_argument("name")
    p_env_add.add_argument("--file", required=True)
    p_env_add.add_argument("--required", action="append", default=[])
    env_sub.add_parser("list", help="List profiles without values")
    p_env_check = env_sub.add_parser("check", help="Check required variable presence")
    p_env_check.add_argument("target")
    p_env_attach = env_sub.add_parser("attach", help="Attach a profile to a repository contract")
    p_env_attach.add_argument("workspace")
    p_env_attach.add_argument("profile")
    p_env_run = env_sub.add_parser("run", help="Run a command with a workspace environment profile")
    p_env_run.add_argument("workspace")
    p_env_run.add_argument("remainder", nargs=argparse.REMAINDER)

    p_fail = sub.add_parser("failures", help="Inspect or record negative operational memory")
    fail_sub = p_fail.add_subparsers(dest="fail_command", required=True)
    p_fail_list = fail_sub.add_parser("list")
    p_fail_list.add_argument("workspace", nargs="?")
    p_fail_add = fail_sub.add_parser("add")
    p_fail_add.add_argument("workspace", nargs="?")
    p_fail_add.add_argument("--command", required=True)
    p_fail_add.add_argument("--signature", required=True)
    p_fail_add.add_argument("--cause", required=True)
    p_fail_add.add_argument("--replacement", required=True)

    p_session = sub.add_parser("session", help="Open, inspect, or close sessions")
    session_sub = p_session.add_subparsers(dest="session_command", required=True)
    p_session_open = session_sub.add_parser("open")
    p_session_open.add_argument("workspace", nargs="?")
    p_session_open.add_argument("--agent", default=os.environ.get("RAO_AGENT", "unknown-agent"))
    p_session_open.add_argument("--objective", required=True)
    p_session_show = session_sub.add_parser("show")
    p_session_show.add_argument("workspace", nargs="?")
    p_session_close = session_sub.add_parser("close")
    p_session_close.add_argument("workspace", nargs="?")
    p_session_close.add_argument("--status", choices=("completed", "blocked", "paused"), required=True)
    p_session_close.add_argument("--next", required=True)

    p_handoff = sub.add_parser("handoff", help="Read or write structured continuity state")
    handoff_sub = p_handoff.add_subparsers(dest="handoff_command", required=True)
    p_handoff_show = handoff_sub.add_parser("show")
    p_handoff_show.add_argument("workspace", nargs="?")
    p_handoff_write = handoff_sub.add_parser("write")
    p_handoff_write.add_argument("workspace", nargs="?")
    p_handoff_write.add_argument("--objective", required=True)
    p_handoff_write.add_argument("--status", choices=("ready", "in_progress", "completed", "blocked", "paused"), required=True)
    p_handoff_write.add_argument("--next", required=True)
    p_handoff_write.add_argument("--completed", action="append", default=[])
    p_handoff_write.add_argument("--remaining", action="append", default=[])

    p_recipe = sub.add_parser("recipe", help="Run a built-in deterministic workflow")
    recipe_sub = p_recipe.add_subparsers(dest="recipe_command", required=True)
    recipe_sub.add_parser("list")
    p_recipe_run = recipe_sub.add_parser("run")
    p_recipe_run.add_argument("name", choices=("start", "baseline", "safe-push", "finish"))
    p_recipe_run.add_argument("workspace", nargs="?")
    p_recipe_run.add_argument("--objective")
    p_recipe_run.add_argument("--agent", default=os.environ.get("RAO_AGENT", "unknown-agent"))
    p_recipe_run.add_argument("--next")
    p_recipe_run.add_argument("--status", choices=("completed", "blocked", "paused"), default="paused")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    paths = RaoPaths.default()
    paths.ensure()
    initialize_global_files(paths)
    registry = WorkspaceRegistry(paths.config)
    store = StateStore(paths.database)
    env_registry = EnvProfileRegistry(paths.secrets)
    runner = CommandRunner(store)

    handlers: dict[str, Callable[[], int]] = {
        "init": lambda: cmd_init(paths),
        "new": lambda: cmd_new(args, paths, registry),
        "onboard": lambda: cmd_onboard(args, paths, registry),
        "refresh": lambda: cmd_refresh(args, registry),
        "projects": lambda: cmd_projects(registry),
        "resolve": lambda: cmd_resolve(args, registry),
        "context": lambda: cmd_context(args, registry, store, env_registry),
        "doctor": lambda: cmd_doctor(args, registry, env_registry),
        "start": lambda: cmd_start(args, registry, store, env_registry),
        "run": lambda: cmd_run(args, registry, store, env_registry, runner),
        "validate": lambda: cmd_validate(args, registry, store, env_registry, runner),
        "push": lambda: cmd_push(args, registry, store, env_registry, runner),
        "commit": lambda: cmd_commit(args, registry, store, env_registry, runner),
        "ship": lambda: cmd_ship(args, registry, store, env_registry, runner),
        "hooks": lambda: cmd_hooks(args, registry),
        "hook": lambda: cmd_hook(args, registry, store, env_registry, runner),
        "scan": lambda: cmd_scan(args, paths, registry),
        "env": lambda: cmd_env(args, registry, env_registry),
        "failures": lambda: cmd_failures(args, registry, store),
        "session": lambda: cmd_session(args, registry, store),
        "handoff": lambda: cmd_handoff(args, registry),
        "recipe": lambda: cmd_recipe(args, registry, store, env_registry, runner),
    }
    try:
        return handlers[args.command]()
    except (KeyError, FileNotFoundError, FileExistsError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


def cmd_init(paths: RaoPaths) -> int:
    initialize_global_files(paths)
    print(f"Ryan Agent OS home: {paths.root}")
    print(f"State database: {paths.database}")
    print("Global policies, recipes, workspace registry, and secret references are ready.")
    return 0


def cmd_new(args, paths: RaoPaths, registry: WorkspaceRegistry) -> int:
    target = Path(args.path).expanduser() if args.path else Path.cwd() / args.name
    create_repository(target, args.name, args.template, args.branch)
    result = onboard_repository(target, paths, registry, workspace_id=args.id)
    if args.hooks:
        install_hooks(result.workspace.path)
    print(f"Created and onboarded: {result.workspace.workspace_id}")
    print(result.workspace.path)
    print(f"Next: rao start {result.workspace.workspace_id} --objective \"Define the first milestone\"")
    return 0


def cmd_onboard(args, paths: RaoPaths, registry: WorkspaceRegistry) -> int:
    result = onboard_repository(
        Path(args.path), paths, registry, workspace_id=args.id, env_profile=args.env_profile, force=args.force
    )
    if args.hooks and (result.workspace.path / ".git").exists():
        installed = install_hooks(result.workspace.path, force=args.force)
        print(f"Installed hooks: {len(installed)}")
    print(f"Onboarded {result.workspace.workspace_id}: {result.workspace.path}")
    print(f"Detected: {result.detected.project_type} / {result.detected.package_manager or 'no package manager'}")
    return 0


def cmd_refresh(args, registry: WorkspaceRegistry) -> int:
    workspace = resolve_workspace(registry, args.workspace)
    contract = refresh_contract(workspace.path)
    print(f"Refreshed {workspace.workspace_id}")
    for name, command in contract.commands.items():
        print(f"  {name}: {command}")
    return 0


def cmd_projects(registry: WorkspaceRegistry) -> int:
    projects = registry.list()
    if not projects:
        print("No workspaces registered. Run `rao onboard .`.")
        return 0
    for item in projects:
        status = "ok" if item.path.exists() else "missing"
        print(f"{item.workspace_id:<28} {status:<8} {item.path}")
    return 0


def cmd_resolve(args, registry: WorkspaceRegistry) -> int:
    workspace = resolve_workspace(registry, args.workspace)
    print(workspace.path)
    return 0


def _profile_for(contract: ProjectContract, env_registry: EnvProfileRegistry) -> EnvProfile | None:
    if not contract.env_profile:
        return None
    return env_registry.get(contract.env_profile)


def cmd_context(args, registry, store, env_registry) -> int:
    workspace = resolve_workspace(registry, args.workspace)
    contract = ProjectContract.load(workspace.path)
    print(render_context(workspace, contract, store, _profile_for(contract, env_registry)))
    return 0


def cmd_doctor(args, registry, env_registry) -> int:
    workspace = resolve_workspace(registry, args.workspace)
    contract = ProjectContract.load(workspace.path)
    checks = run_doctor(workspace, contract, _profile_for(contract, env_registry))
    print(render_checks(checks))
    return 1 if any(not item.ok and item.blocking for item in checks) else 0


def cmd_start(args, registry, store, env_registry) -> int:
    workspace = resolve_workspace(registry, args.workspace)
    contract = ProjectContract.load(workspace.path)
    checks = run_doctor(workspace, contract, _profile_for(contract, env_registry))
    print(render_checks(checks))
    if any(not item.ok and item.blocking for item in checks):
        print("Session was not opened because doctor found blocking failures.", file=sys.stderr)
        return 1
    active = store.active_session(workspace.workspace_id)
    if active:
        print(f"Active session already exists: {active['id']}")
    else:
        session_id = store.open_session(workspace.workspace_id, args.agent, args.objective)
        print(f"Opened session: {session_id}")
    print()
    print(render_context(workspace, contract, store, _profile_for(contract, env_registry)))
    return 0


def cmd_run(args, registry, store, env_registry, runner) -> int:
    workspace = resolve_workspace(registry, args.workspace)
    contract = ProjectContract.load(workspace.path)
    result = runner.run_named(
        workspace.path, contract, args.command_name, _profile_for(contract, env_registry), force=args.force
    )
    if result.blocked:
        print(result.stderr, file=sys.stderr)
    return result.exit_code


def run_validation(workspace, contract, env_profile, runner, force=False) -> tuple[int, dict[str, str]]:
    results: dict[str, str] = {}
    executed = 0
    for name in VALIDATION_ORDER:
        if name not in contract.commands:
            continue
        executed += 1
        print(f"\n== {name}: {contract.commands[name]} ==")
        result = runner.run_named(workspace.path, contract, name, env_profile, force=force)
        results[name] = "passed" if result.exit_code == 0 else ("blocked" if result.blocked else "failed")
        if result.blocked:
            print(result.stderr, file=sys.stderr)
        if result.exit_code != 0:
            return result.exit_code, results
    if executed == 0:
        print("No validation commands are declared. Edit .agent/project.toml or run `rao refresh`.")
        return 0, results
    return 0, results


def cmd_validate(args, registry, store, env_registry, runner) -> int:
    workspace = resolve_workspace(registry, args.workspace)
    contract = ProjectContract.load(workspace.path)
    code, results = run_validation(workspace, contract, _profile_for(contract, env_registry), runner, args.force)
    print("\nValidation summary:")
    for name, status in results.items():
        print(f"  {name:<12} {status}")
    return code


def cmd_push(args, registry, store, env_registry, runner) -> int:
    workspace = resolve_workspace(registry, args.workspace)
    contract = ProjectContract.load(workspace.path)
    git = git_state(workspace.path, contract.remote)
    if not git.is_repo:
        raise RuntimeError("Workspace is not a Git repository")
    if not git.branch:
        raise RuntimeError("Detached HEAD; push aborted")
    policies = load_policies(RaoPaths.default().config)
    if git.branch in policies.protected_branches and not args.allow_protected:
        raise RuntimeError(f"Protected branch `{git.branch}`; create a feature branch or pass --allow-protected intentionally")
    if policies.require_clean_worktree_before_push and not git.clean and not args.allow_dirty:
        raise RuntimeError("Working tree is dirty; commit or stash changes before push, or pass --allow-dirty intentionally")
    if policies.require_validation_before_push and not args.skip_validation:
        code, _ = run_validation(
            workspace, contract, _profile_for(contract, env_registry), runner, force=args.force_run
        )
        if code != 0:
            print("Push aborted because validation did not pass.", file=sys.stderr)
            return code
    if git.remote_url and "github.com" in git.remote_url:
        ok, detail = gh_auth_ok(workspace.path)
        if not ok:
            print("GitHub CLI authentication warning:", detail, file=sys.stderr)
            print("Continuing because Git may use SSH or another credential helper.", file=sys.stderr)
    env = dict(os.environ)
    env["RAO_VALIDATED"] = "1"
    if args.allow_protected:
        env["RAO_ALLOW_PROTECTED"] = "1"
    command = ["git", "push", "--set-upstream", contract.remote, git.branch]
    print("Executing:", " ".join(shlex.quote(part) for part in command), flush=True)
    result = subprocess.run(command, cwd=workspace.path, env=env, check=False)
    return result.returncode



def cmd_commit(args, registry, store, env_registry, runner) -> int:
    workspace = resolve_workspace(registry, args.workspace)
    contract = ProjectContract.load(workspace.path)
    git = git_state(workspace.path, contract.remote)
    if not git.is_repo:
        raise RuntimeError("Workspace is not a Git repository")
    if not git.branch:
        raise RuntimeError("Detached HEAD; commit aborted")
    validation_results: dict[str, str] = {}
    if not args.skip_validation:
        code, validation_results = run_validation(
            workspace, contract, _profile_for(contract, env_registry), runner, force=args.force_run
        )
        if code != 0:
            print("Commit aborted because validation did not pass.", file=sys.stderr)
            return code
    if args.all:
        staged = subprocess.run(["git", "add", "-A"], cwd=workspace.path, check=False)
        if staged.returncode != 0:
            return staged.returncode
    staged_names = subprocess.run(
        ["git", "diff", "--cached", "--name-only"], cwd=workspace.path,
        check=False, capture_output=True, text=True
    )
    if staged_names.returncode != 0:
        return staged_names.returncode
    if not staged_names.stdout.strip():
        raise RuntimeError("No staged changes. Stage files first or pass --all.")
    sensitive = sensitive_staged_files(workspace.path)
    if sensitive and not args.allow_sensitive:
        formatted = "\n  - ".join(sensitive)
        raise RuntimeError(
            "Potential secret files are staged; commit blocked:\n  - " + formatted +
            "\nRemove them from staging or pass --allow-sensitive only after manual review."
        )
    command = ["git", "commit", "-m", args.message]
    print("Executing:", " ".join(shlex.quote(part) for part in command), flush=True)
    result = subprocess.run(command, cwd=workspace.path, check=False)
    if result.returncode == 0 and validation_results:
        post_commit_fingerprint = fingerprint(workspace.path, workspace.path / ".agent" / "project.toml")
        for name, status in validation_results.items():
            if status == "passed" and name in contract.commands:
                store.record_validation(
                    workspace.workspace_id,
                    post_commit_fingerprint,
                    name,
                    contract.commands[name],
                    0,
                )
    return result.returncode


def cmd_ship(args, registry, store, env_registry, runner) -> int:
    commit_code = cmd_commit(
        argparse.Namespace(
            workspace=args.workspace,
            message=args.message,
            all=args.all,
            skip_validation=False,
            allow_sensitive=args.allow_sensitive,
            force_run=args.force_run,
        ),
        registry, store, env_registry, runner,
    )
    if commit_code != 0:
        return commit_code
    return cmd_push(
        argparse.Namespace(
            workspace=args.workspace,
            skip_validation=True,
            allow_dirty=False,
            allow_protected=args.allow_protected,
            force_run=args.force_run,
        ),
        registry, store, env_registry, runner,
    )

def cmd_hooks(args, registry) -> int:
    workspace = resolve_workspace(registry, args.workspace)
    installed = install_hooks(workspace.path, force=args.force)
    for path in installed:
        print(f"Installed: {path}")
    if not installed:
        print("No hooks changed. Existing unmanaged hooks were preserved; use --force only after reviewing them.")
    return 0


def cmd_hook(args, registry, store, env_registry, runner) -> int:
    if args.hook_name == "pre-push" and os.environ.get("RAO_VALIDATED") == "1":
        return 0
    workspace = resolve_workspace(registry, None)
    contract = ProjectContract.load(workspace.path)
    if args.hook_name == "pre-push":
        git = git_state(workspace.path, contract.remote)
        policies = load_policies(RaoPaths.default().config)
        if git.branch in policies.protected_branches and os.environ.get("RAO_ALLOW_PROTECTED") != "1":
            print(
                f"Push blocked: `{git.branch}` is protected. Use a feature branch or `rao push --allow-protected`.",
                file=sys.stderr,
            )
            return 1
        code, _ = run_validation(workspace, contract, _profile_for(contract, env_registry), runner)
        return code
    if args.hook_name == "post-commit":
        git = git_state(workspace.path, contract.remote)
        store.record_event(
            workspace.workspace_id,
            "commit",
            {
                "commit": git.commit,
                "branch": git.branch,
                "fingerprint": fingerprint(workspace.path, workspace.path / ".agent" / "project.toml"),
            },
        )
        return 0
    if args.hook_name == "post-checkout":
        print(f"Ryan Agent OS: {workspace.workspace_id}")
        print(f"Run `rao context {workspace.workspace_id}` for the authoritative next action.")
        return 0
    return 0


def cmd_scan(args, paths, registry) -> int:
    if args.depth < 0 or args.depth > 8:
        raise ValueError("Depth must be between 0 and 8")
    repos = find_git_repositories(Path(args.root), args.depth)
    if not repos:
        print("No Git repositories found within the bounded search.")
        return 0
    for repo in repos:
        print(repo)
        if args.register:
            try:
                if registry.find_for_path(repo):
                    continue
                result = onboard_repository(repo, paths, registry)
                print(f"  registered as {result.workspace.workspace_id}")
            except FileExistsError:
                contract = ProjectContract.load(repo)
                registry.register(contract.workspace_id, repo, contract.remote, contract.default_branch)
                print(f"  registered existing contract as {contract.workspace_id}")
    return 0


def cmd_env(args, registry, env_registry) -> int:
    if args.env_command == "add":
        location = Path(args.file).expanduser().resolve()
        if not location.exists():
            raise FileNotFoundError(f"Environment file does not exist: {location}")
        env_registry.add(EnvProfile(args.name, "dotenv", location, tuple(args.required)))
        print(f"Registered environment profile `{args.name}` -> {location}")
        print("Secret values were not copied or displayed.")
        return 0
    if args.env_command == "list":
        for profile in env_registry.list():
            print(f"{profile.name:<24} {profile.provider:<10} {profile.location or '-'} required={len(profile.required)}")
        return 0
    if args.env_command == "attach":
        workspace = registry.resolve(args.workspace)
        env_registry.get(args.profile)
        set_env_profile(workspace.path, args.profile)
        print(f"Attached environment profile `{args.profile}` to `{workspace.workspace_id}`.")
        return 0
    if args.env_command == "check":
        try:
            workspace = registry.resolve(args.target)
        except KeyError:
            profile = env_registry.get(args.target)
        else:
            contract = ProjectContract.load(workspace.path)
            if not contract.env_profile:
                raise ValueError(f"Workspace `{workspace.workspace_id}` has no env_profile in .agent/project.toml")
            profile = env_registry.get(contract.env_profile)
        result = EnvBroker().check(profile)
        print(result.render())
        return 0 if result.valid else 1
    if args.env_command == "run":
        workspace = registry.resolve(args.workspace)
        contract = ProjectContract.load(workspace.path)
        if not contract.env_profile:
            raise ValueError(f"Workspace `{workspace.workspace_id}` has no environment profile")
        command = list(args.remainder)
        if command and command[0] == "--":
            command = command[1:]
        if not command:
            raise ValueError("Provide a command after `--`")
        return EnvBroker().run(env_registry.get(contract.env_profile), command, workspace.path)
    return 2


def cmd_failures(args, registry, store) -> int:
    workspace = resolve_workspace(registry, args.workspace)
    if args.fail_command == "list":
        failures = store.list_failures(workspace.workspace_id)
        if not failures:
            print("No failures recorded.")
            return 0
        for item in failures:
            print(f"[{item['status']}] {item['command']}")
            print(f"  signature: {item['error_signature']}")
            if item.get("root_cause"):
                print(f"  cause: {item['root_cause']}")
            if item.get("replacement_action"):
                print(f"  replacement: {item['replacement_action']}")
        return 0
    store.record_failure(
        workspace.workspace_id, args.command, args.signature, args.cause, args.replacement
    )
    print("Failure memory recorded.")
    return 0


def cmd_session(args, registry, store) -> int:
    workspace = resolve_workspace(registry, args.workspace)
    if args.session_command == "open":
        active = store.active_session(workspace.workspace_id)
        if active:
            print(json.dumps(active, indent=2))
            return 0
        print(store.open_session(workspace.workspace_id, args.agent, args.objective))
        return 0
    if args.session_command == "show":
        session = store.active_session(workspace.workspace_id) or store.latest_session(workspace.workspace_id)
        print(json.dumps(session or {}, indent=2))
        return 0
    active = store.active_session(workspace.workspace_id)
    if not active:
        raise KeyError(f"No active session for {workspace.workspace_id}")
    store.close_session(active["id"], args.status, args.next)
    print(f"Closed {active['id']} as {args.status}")
    return 0


def cmd_handoff(args, registry) -> int:
    workspace = resolve_workspace(registry, args.workspace)
    contract = ProjectContract.load(workspace.path)
    if args.handoff_command == "show":
        print(json.dumps(read_handoff(workspace.path), indent=2))
        return 0
    handoff = write_handoff(
        workspace.path,
        contract,
        args.objective,
        args.status,
        args.next,
        completed=args.completed,
        remaining=args.remaining,
    )
    print(json.dumps(handoff, indent=2))
    return 0


def cmd_recipe(args, registry, store, env_registry, runner) -> int:
    if args.recipe_command == "list":
        print("start       doctor + session open + context")
        print("baseline    test + lint + typecheck + build")
        print("safe-push   validation + protected push")
        print("finish      handoff + session close")
        return 0
    workspace = resolve_workspace(registry, args.workspace)
    if args.name == "start":
        if not args.objective:
            raise ValueError("Recipe `start` requires --objective")
        return cmd_start(
            argparse.Namespace(workspace=workspace.workspace_id, agent=args.agent, objective=args.objective),
            registry, store, env_registry
        )
    if args.name == "baseline":
        return cmd_validate(
            argparse.Namespace(workspace=workspace.workspace_id, force=False),
            registry, store, env_registry, runner
        )
    if args.name == "safe-push":
        return cmd_push(
            argparse.Namespace(
                workspace=workspace.workspace_id, skip_validation=False, allow_dirty=False,
                allow_protected=False, force_run=False
            ),
            registry, store, env_registry, runner
        )
    if args.name == "finish":
        if not args.objective or not args.next:
            raise ValueError("Recipe `finish` requires --objective and --next")
        code = cmd_handoff(
            argparse.Namespace(
                workspace=workspace.workspace_id, handoff_command="write", objective=args.objective,
                status=args.status, next=args.next, completed=[], remaining=[]
            ),
            registry
        )
        if code != 0:
            return code
        active = store.active_session(workspace.workspace_id)
        if active:
            store.close_session(active["id"], args.status, args.next)
            print(f"Closed session: {active['id']}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
