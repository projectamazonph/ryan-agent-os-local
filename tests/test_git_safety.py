import tempfile
import unittest
from pathlib import Path
import subprocess

from rao.git import sensitive_staged_files


class GitSafetyTests(unittest.TestCase):
    def test_detects_staged_secret_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            (root / ".env").write_text("SECRET=value\n")
            (root / "app.py").write_text("print('ok')\n")
            subprocess.run(["git", "add", "."], cwd=root, check=True)

            found = sensitive_staged_files(root)

            self.assertIn(".env", found)
            self.assertNotIn("app.py", found)

    def test_allows_documented_env_example(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            (root / ".env.example").write_text("API_KEY=replace-me\n")
            subprocess.run(["git", "add", "-f", ".env.example"], cwd=root, check=True)

            found = sensitive_staged_files(root)

            self.assertNotIn(".env.example", found)


if __name__ == "__main__":
    unittest.main()
