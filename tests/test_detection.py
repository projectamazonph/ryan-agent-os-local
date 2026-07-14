import json
import tempfile
import unittest
from pathlib import Path

from rao.detection import detect_project


class DetectionTests(unittest.TestCase):
    def test_detects_pnpm_node_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(json.dumps({
                "name": "demo-app",
                "scripts": {
                    "test": "vitest run",
                    "lint": "eslint .",
                    "typecheck": "tsc --noEmit",
                    "build": "vite build",
                    "dev": "vite"
                }
            }))
            (root / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n")

            result = detect_project(root)

            self.assertEqual(result.project_type, "node")
            self.assertEqual(result.package_manager, "pnpm")
            self.assertEqual(result.name, "demo-app")
            self.assertEqual(result.commands["test"], "pnpm test")
            self.assertEqual(result.commands["typecheck"], "pnpm typecheck")

    def test_detects_python_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text("[project]\nname='demo-python'\n")
            (root / "tests").mkdir()

            result = detect_project(root)

            self.assertEqual(result.project_type, "python")
            self.assertEqual(result.name, "demo-python")
            self.assertIn("unittest", result.commands["test"])


if __name__ == "__main__":
    unittest.main()
