import tempfile
import unittest
from pathlib import Path

from rao.project import ProjectContract, set_env_profile
from rao.tomlutil import dump_project_toml


class ContractUpdateTests(unittest.TestCase):
    def test_set_env_profile_preserves_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".agent").mkdir()
            data = {
                "project": "demo",
                "workspace_id": "demo",
                "project_type": "node",
                "package_manager": "pnpm",
                "env_profile": None,
                "commands": {"test": "pnpm test"},
                "remote": "origin",
                "default_branch": "main",
            }
            (root / ".agent" / "project.toml").write_text(dump_project_toml(data))

            set_env_profile(root, "demo-env")
            contract = ProjectContract.load(root)

            self.assertEqual(contract.env_profile, "demo-env")
            self.assertEqual(contract.commands["test"], "pnpm test")


if __name__ == "__main__":
    unittest.main()
