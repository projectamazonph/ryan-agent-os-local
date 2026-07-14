import tempfile
import unittest
from pathlib import Path

from rao.state import StateStore
from rao.guard import RepetitionGuard


class RepetitionGuardTests(unittest.TestCase):
    def test_blocks_identical_failed_command_for_same_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore(Path(tmp) / "state.db")
            guard = RepetitionGuard(store)
            guard.record("demo", "abc", "pnpm build", 1, "same error")

            decision = guard.check("demo", "abc", "pnpm build")

            self.assertFalse(decision.allowed)
            self.assertIn("previously failed", decision.reason)

    def test_allows_command_when_fingerprint_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore(Path(tmp) / "state.db")
            guard = RepetitionGuard(store)
            guard.record("demo", "abc", "pnpm build", 1, "same error")

            decision = guard.check("demo", "xyz", "pnpm build")

            self.assertTrue(decision.allowed)


if __name__ == "__main__":
    unittest.main()
