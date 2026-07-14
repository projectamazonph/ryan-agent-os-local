import json
import tempfile
import unittest
from pathlib import Path

from rao.onboard import onboard_repository
from rao.paths import RaoPaths
from rao.registry import WorkspaceRegistry


class OnboardTests(unittest.TestCase):
    def test_onboard_creates_agent_contract_and_registers_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            repo = root / "demo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / "package.json").write_text(json.dumps({"name": "demo", "scripts": {"test": "vitest run"}}))
            (repo / "package-lock.json").write_text("{}")
            paths = RaoPaths.from_home(home)
            paths.ensure()
            registry = WorkspaceRegistry(paths.config)

            result = onboard_repository(repo, paths, registry, workspace_id="demo")

            self.assertTrue((repo / ".agent" / "project.toml").exists())
            self.assertTrue((repo / ".agent" / "current-state.md").exists())
            self.assertTrue((repo / ".agent" / "handoff.json").exists())
            self.assertEqual(result.workspace.workspace_id, "demo")
            self.assertEqual(registry.resolve("demo").path, repo.resolve())


if __name__ == "__main__":
    unittest.main()
