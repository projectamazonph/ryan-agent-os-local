from __future__ import annotations

import json
from pathlib import Path

from .git import init_repo


def create_repository(path: Path, name: str, template: str, default_branch: str = "main") -> None:
    path = path.expanduser().resolve()
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(f"Target directory is not empty: {path}")
    path.mkdir(parents=True, exist_ok=True)
    init_repo(path, default_branch)
    (path / "README.md").write_text(f"# {name}\n\nManaged with Ryan Agent OS.\n", encoding="utf-8")
    (path / ".gitignore").write_text(_gitignore(template), encoding="utf-8")
    if template == "node":
        package = {
            "name": _slug(name),
            "version": "0.1.0",
            "private": True,
            "type": "module",
            "scripts": {"test": "node --test"},
        }
        (path / "package.json").write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
        (path / "test").mkdir(exist_ok=True)
        (path / "test" / "smoke.test.js").write_text(
            "import test from 'node:test';\nimport assert from 'node:assert/strict';\n\n"
            "test('repository baseline', () => {\n  assert.equal(1 + 1, 2);\n});\n",
            encoding="utf-8",
        )
    elif template == "python":
        (path / "pyproject.toml").write_text(
            "[build-system]\nrequires = [\"setuptools>=68\"]\nbuild-backend = \"setuptools.build_meta\"\n\n"
            f"[project]\nname = \"{_slug(name)}\"\nversion = \"0.1.0\"\nrequires-python = \">=3.11\"\n",
            encoding="utf-8",
        )
        (path / "src" / _slug(name).replace("-", "_")).mkdir(parents=True, exist_ok=True)
        (path / "tests").mkdir(exist_ok=True)
        (path / "tests" / "test_smoke.py").write_text(
            "import unittest\n\n\n"
            "class SmokeTest(unittest.TestCase):\n"
            "    def test_repository_baseline(self):\n"
            "        self.assertEqual(1 + 1, 2)\n\n\n"
            "if __name__ == '__main__':\n"
            "    unittest.main()\n",
            encoding="utf-8",
        )


def _slug(value: str) -> str:
    result = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return "-".join(part for part in result.split("-") if part)


def _gitignore(template: str) -> str:
    common = ".env\n.env.*\n!.env.example\n.DS_Store\nThumbs.db\n"
    if template == "node":
        return common + "node_modules/\ndist/\ncoverage/\n"
    if template == "python":
        return common + "__pycache__/\n*.py[cod]\n.venv/\ndist/\nbuild/\n*.egg-info/\n"
    return common
