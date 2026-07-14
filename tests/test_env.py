import tempfile
import unittest
from pathlib import Path

from rao.env import EnvBroker, EnvProfile


class EnvBrokerTests(unittest.TestCase):
    def test_reports_only_presence_not_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "demo.env"
            env_file.write_text("API_KEY=super-secret\nDATABASE_URL=postgres://example\n")
            broker = EnvBroker()
            profile = EnvProfile(
                name="demo",
                provider="dotenv",
                location=env_file,
                required=("API_KEY", "DATABASE_URL", "MISSING_KEY"),
            )

            result = broker.check(profile)

            self.assertTrue(result.present["API_KEY"])
            self.assertFalse(result.present["MISSING_KEY"])
            rendered = result.render()
            self.assertNotIn("super-secret", rendered)
            self.assertNotIn("postgres://example", rendered)


if __name__ == "__main__":
    unittest.main()
