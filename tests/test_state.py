import tempfile
import unittest
from pathlib import Path

from rao.state import StateStore


class StateStoreTests(unittest.TestCase):
    def test_records_session_and_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "state.db"
            store = StateStore(db_path)
            session_id = store.open_session("demo", "codex", "Build feature")
            store.record_failure(
                workspace_id="demo",
                command="pnpm build",
                error_signature="exit:1:abc123",
                root_cause="Missing environment variable",
                replacement_action="Run rao env check demo",
            )
            store.record_validation("demo", "fp1", "test", "python -m unittest", 0)
            store.record_event("demo", "commit", {"commit": "abc123"})
            store.close_session(session_id, "blocked", "Fix environment profile")

            session = store.latest_session("demo")
            failures = store.list_failures("demo")

            self.assertEqual(session["status"], "blocked")
            self.assertEqual(session["next_action"], "Fix environment profile")
            self.assertEqual(len(failures), 1)
            self.assertEqual(failures[0]["command"], "pnpm build")
            validations = store.latest_validations("demo", "fp1")
            events = store.list_events("demo")
            self.assertEqual(validations["test"]["exit_code"], 0)
            self.assertEqual(events[0]["event_type"], "commit")


if __name__ == "__main__":
    unittest.main()
