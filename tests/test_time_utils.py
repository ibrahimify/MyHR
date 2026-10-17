import unittest
from datetime import UTC, datetime
from pathlib import Path

from src.core.time import utc_now


class UtcNowTests(unittest.TestCase):
    def test_returns_recent_naive_utc_datetime(self):
        before = datetime.now(UTC).replace(tzinfo=None)
        value = utc_now()
        after = datetime.now(UTC).replace(tzinfo=None)

        self.assertIsNone(value.tzinfo)
        self.assertLessEqual(before, value)
        self.assertLessEqual(value, after)

    def test_application_source_does_not_use_deprecated_utcnow(self):
        source_root = Path(__file__).resolve().parents[1] / "src"
        offenders = [
            str(path.relative_to(source_root))
            for path in source_root.rglob("*.py")
            if "datetime.utcnow" in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
