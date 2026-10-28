from hashlib import sha256
from pathlib import Path
import re
import unittest


ARCHIVE_ROOT = Path("docs/archive")
MANIFEST_PATH = ARCHIVE_ROOT / "MANIFEST.md"
ROW_PATTERN = re.compile(
    r"^\| `(?P<path>[^`]+)` \| (?P<size>[\d,]+) \| `(?P<digest>[0-9a-f]{64})` \|$"
)


class ArchiveManifestTests(unittest.TestCase):
    def test_manifest_covers_and_verifies_every_archived_file(self):
        rows = {}
        for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines():
            match = ROW_PATTERN.match(line)
            if match:
                rows[match.group("path")] = (
                    int(match.group("size").replace(",", "")),
                    match.group("digest"),
                )

        archived_files = {
            path.relative_to(ARCHIVE_ROOT).as_posix()
            for path in ARCHIVE_ROOT.rglob("*")
            if path.is_file() and path.name != "MANIFEST.md"
        }
        self.assertEqual(set(rows), archived_files)

        for relative_path, (expected_size, expected_digest) in rows.items():
            path = ARCHIVE_ROOT / relative_path
            body = path.read_bytes()
            self.assertEqual(len(body), expected_size, relative_path)
            self.assertEqual(sha256(body).hexdigest(), expected_digest, relative_path)


if __name__ == "__main__":
    unittest.main()
