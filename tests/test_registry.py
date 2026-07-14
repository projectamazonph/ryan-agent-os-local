import tempfile
import unittest
from pathlib import Path

from rao.registry import WorkspaceRegistry


class WorkspaceRegistryTests(unittest.TestCase):
    def test_register_and_resolve_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp) / "config"
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            registry = WorkspaceRegistry(config_dir)

            registry.register("demo", project_dir, "origin", "main")
            workspace = registry.resolve("demo")

            self.assertEqual(workspace.workspace_id, "demo")
            self.assertEqual(workspace.path, project_dir.resolve())
            self.assertEqual(workspace.default_branch, "main")

    def test_resolve_accepts_registered_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp) / "config"
            project_dir = Path(tmp) / "project"
            project_dir.mkdir()
            registry = WorkspaceRegistry(config_dir)
            registry.register("demo", project_dir, "origin", "main")

            workspace = registry.resolve(str(project_dir))

            self.assertEqual(workspace.workspace_id, "demo")


if __name__ == "__main__":
    unittest.main()
