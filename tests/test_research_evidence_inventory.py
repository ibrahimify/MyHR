import contextlib
from hashlib import sha256
import io
import json
from pathlib import Path
import tempfile
import unittest

from scripts.inventory_research_evidence import build_inventory, main, write_inventory


class ResearchEvidenceInventoryTests(unittest.TestCase):
    def _write_complete_artifact(self, root: Path, relative: str) -> Path:
        artifact = root / relative
        artifact.mkdir(parents=True)
        body = b"development evidence\n"
        (artifact / "result.csv").write_bytes(body)
        (artifact / "manifest.json").write_text(
            json.dumps(
                {
                    "algorithm": "sha256",
                    "files": {"result.csv": sha256(body).hexdigest()},
                }
            ),
            encoding="utf-8",
        )
        return artifact

    def test_inventory_verifies_manifest_and_detects_incomplete_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "research_outputs"
            self._write_complete_artifact(root, "protocol/run_valid")
            (root / "protocol" / "run_empty").mkdir()
            incomplete = root / "legacy"
            incomplete.mkdir(parents=True)
            (incomplete / "results.csv").write_text("x\n", encoding="utf-8")

            inventory = build_inventory(root, base / "private-notes")
            by_path = {entry["path"]: entry for entry in inventory["artifacts"]}

            self.assertEqual(by_path["protocol/run_valid"]["state"], "complete")
            self.assertEqual(
                by_path["protocol/run_valid"]["manifest"]["status"], "valid"
            )
            self.assertEqual(by_path["protocol/run_empty"]["state"], "orphan_empty")
            self.assertEqual(by_path["legacy"]["state"], "incomplete_missing_manifest")

    def test_collection_sidecars_do_not_turn_collection_into_artifact(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "research_outputs"
            self._write_complete_artifact(root, "protocol/run_valid")
            (root / "protocol" / "run_valid.audit.json").write_text(
                "{}\n", encoding="utf-8"
            )

            inventory = build_inventory(root, base / "private-notes")
            paths = {entry["path"] for entry in inventory["artifacts"]}

            self.assertNotIn("protocol", paths)
            self.assertIn("protocol/run_valid", paths)

    def test_release_checksum_sidecar_is_verified_without_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "research_outputs"
            release = root / "releases"
            release.mkdir(parents=True)
            body = b"immutable release evidence\n"
            archive = release / "evidence.zip"
            archive.write_bytes(body)
            (release / "evidence.zip.sha256").write_text(
                f"{sha256(body).hexdigest()}  evidence.zip\n",
                encoding="ascii",
            )

            inventory = build_inventory(root, base / "private-notes")
            artifact = inventory["artifacts"][0]

            self.assertEqual(artifact["state"], "complete")
            self.assertEqual(artifact["manifest"]["source"], "sha256_sidecars")
            self.assertEqual(artifact["manifest"]["verified_file_count"], 1)

    def test_duplicate_release_sidecars_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "research_outputs"
            release = root / "releases"
            release.mkdir(parents=True)
            body = b"immutable release evidence\n"
            (release / "evidence.zip").write_bytes(body)
            digest = sha256(body).hexdigest()
            for sidecar_name in ("evidence.zip.sha256", "duplicate.sha256"):
                (release / sidecar_name).write_text(
                    f"{digest}  evidence.zip\n", encoding="ascii"
                )

            inventory = build_inventory(root, base / "private-notes")
            artifact = inventory["artifacts"][0]

            self.assertEqual(artifact["state"], "integrity_problem")
            self.assertTrue(
                any(
                    "duplicate checksum target" in issue
                    for issue in artifact["manifest"]["issues"]
                )
            )

    def test_inventory_reports_tampering_without_reading_private_note_contents(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "research_outputs"
            artifact = self._write_complete_artifact(root, "protocol/run_tampered")
            (artifact / "result.csv").write_text("changed\n", encoding="utf-8")
            private = base / "private-notes"
            private.mkdir()
            secret_name = "never-report-this-name.md"
            secret_text = "private research thought"
            (private / secret_name).write_text(secret_text, encoding="utf-8")

            inventory = build_inventory(root, private)
            encoded = json.dumps(inventory)

            self.assertEqual(inventory["artifacts"][0]["state"], "integrity_problem")
            self.assertNotIn(secret_name, encoded)
            self.assertNotIn(secret_text, encoded)
            self.assertFalse(inventory["safety"]["private_note_contents_inspected"])

    def test_holdout_named_subtree_is_opaque(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "research_outputs"
            self._write_complete_artifact(root, "development/run_valid")
            holdout = root / "final_holdout_secret"
            holdout.mkdir(parents=True)
            forbidden = "must-not-appear.csv"
            (holdout / forbidden).write_text("do not inspect", encoding="utf-8")

            inventory = build_inventory(root, base / "private-notes")
            encoded = json.dumps(inventory)

            self.assertNotIn("final_holdout_secret", encoded)
            self.assertNotIn(forbidden, encoded)
            self.assertEqual(inventory["summary"]["skipped_holdout_entries"], 1)
            self.assertFalse(inventory["safety"]["holdout_content_inspected"])

    def test_opaque_entry_prevents_complete_artifact_classification(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "research_outputs"
            artifact = self._write_complete_artifact(root, "development/run_valid")
            (artifact / "holdout_opaque.bin").write_bytes(b"not inspected")

            inventory = build_inventory(root, base / "private-notes")
            result = inventory["artifacts"][0]

            self.assertEqual(result["state"], "review_required_opaque_entries")
            self.assertEqual(result["manifest"]["status"], "valid")
            self.assertEqual(result["file_count"], 2)

    def test_manifest_cannot_escape_artifact_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "research_outputs"
            artifact = root / "protocol" / "run_unsafe"
            artifact.mkdir(parents=True)
            (artifact / "manifest.json").write_text(
                json.dumps({"algorithm": "sha256", "files": {"../secret": "0" * 64}}),
                encoding="utf-8",
            )

            inventory = build_inventory(root, base / "private-notes")

            manifest = inventory["artifacts"][0]["manifest"]
            self.assertEqual(manifest["status"], "failed")
            self.assertIn("unsafe or holdout-like", manifest["issues"][0])
            self.assertNotIn("../secret", json.dumps(inventory))

    def test_holdout_named_private_root_is_not_entered(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "research_outputs"
            self._write_complete_artifact(root, "development/run_valid")
            private = base / "private_holdout_notes"
            private.mkdir()
            (private / "secret.md").write_text("private", encoding="utf-8")

            inventory = build_inventory(root, private)

            self.assertEqual(inventory["private_notes"]["file_count"], 0)
            self.assertEqual(inventory["private_notes"]["skipped_holdout_entries"], 1)

    def test_output_is_write_once_and_requires_ignored_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "inventory.json"
            inventory = {"schema_version": 1}
            write_inventory(inventory, output, ignore_checker=lambda _path: True)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), inventory)
            with self.assertRaises(FileExistsError):
                write_inventory(inventory, output, ignore_checker=lambda _path: True)
            with self.assertRaisesRegex(ValueError, "ignored by Git"):
                write_inventory(
                    inventory,
                    Path(temporary) / "tracked.json",
                    ignore_checker=lambda _path: False,
                )

    def test_cli_defaults_to_json_on_stdout(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "research_outputs"
            self._write_complete_artifact(root, "development/run_valid")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--artifact-root",
                        str(root),
                        "--private-notes-root",
                        str(base / "private-notes"),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(stdout.getvalue())["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()
