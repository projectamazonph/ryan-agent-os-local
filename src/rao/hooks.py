from __future__ import annotations

from pathlib import Path
import os


HOOKS = {
    "pre-push": """#!/usr/bin/env sh
set -eu
if [ "${RAO_VALIDATED:-}" = "1" ]; then
  exit 0
fi
RAO_CMD=${RAO_EXECUTABLE:-rao}
if [ -x "$RAO_CMD" ] || command -v "$RAO_CMD" >/dev/null 2>&1; then
  "$RAO_CMD" hook pre-push
else
  echo "Ryan Agent OS is unavailable; push blocked because validation cannot run." >&2
  exit 1
fi
""",
    "post-commit": """#!/usr/bin/env sh
set -eu
RAO_CMD=${RAO_EXECUTABLE:-rao}
if [ -x "$RAO_CMD" ] || command -v "$RAO_CMD" >/dev/null 2>&1; then
  "$RAO_CMD" hook post-commit || true
fi
""",
    "post-checkout": """#!/usr/bin/env sh
set -eu
RAO_CMD=${RAO_EXECUTABLE:-rao}
if [ -x "$RAO_CMD" ] || command -v "$RAO_CMD" >/dev/null 2>&1; then
  "$RAO_CMD" hook post-checkout || true
fi
""",
}


def install_hooks(root: Path, force: bool = False) -> list[Path]:
    git_dir = root / ".git"
    if not git_dir.exists():
        raise FileNotFoundError(f"Not a Git repository: {root}")
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    installed: list[Path] = []
    for name, content in HOOKS.items():
        path = hooks_dir / name
        if path.exists() and not force:
            existing = path.read_text(encoding="utf-8", errors="ignore")
            if "Ryan Agent OS" not in existing and "rao hook" not in existing:
                continue
        path.write_text(content, encoding="utf-8")
        try:
            path.chmod(path.stat().st_mode | 0o111)
        except OSError:
            pass
        installed.append(path)
    return installed
