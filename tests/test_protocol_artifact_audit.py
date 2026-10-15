import csv
import json
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from scripts.audit_tdk_protocol_artifact import ArtifactAuditError, audit_artifact


class ProtocolArtifactAuditTests(unittest.TestCase):
    def test_audit_recomputes_counts_and_rates(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            self._write_fixture(run_dir)

            result = audit_artifact(run_dir, Path.cwd())

            self.assertEqual(result["status"], "verified")
            self.assertEqual(result["scenario_count"], 1)
            self.assertEqual(result["prediction_rows"], 2)

    def test_audit_rejects_tampered_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            self._write_fixture(run_dir)
            (run_dir / "record_predictions.csv").write_text("tampered\n", encoding="utf-8")

            with self.assertRaisesRegex(ArtifactAuditError, "checksum mismatch"):
                audit_artifact(run_dir, Path.cwd())

    @staticmethod
    def _write_fixture(run_dir: Path) -> None:
        metadata = {
            "artifact_id": "fixture",
            "holdout_accessed": False,
            "protocol_status": "draft_validation_holdout_locked",
            "protocol_version": "fixture",
            "run_purpose": "validation",
            "provenance": {
                "git_commit": "HEAD",
                "git_dirty": False,
                "source_sha256": {},
            },
        }
        (run_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
        (run_dir / "README.md").write_text("fixture\n", encoding="utf-8")
        predictions = [
            {
                "scenario_id": "s1",
                "employee_id": "E1",
                "method": "deterministic_policy_rules",
                "representation": "true_policy_checks",
                "operating_point": "rules_fixed",
                "predicted_anomaly": "True",
                "ground_truth_anomaly": "True",
                "labels": "inconsistent_dates",
            },
            {
                "scenario_id": "s1",
                "employee_id": "E2",
                "method": "deterministic_policy_rules",
                "representation": "true_policy_checks",
                "operating_point": "rules_fixed",
                "predicted_anomaly": "False",
                "ground_truth_anomaly": "False",
                "labels": "clean",
            },
        ]
        ProtocolArtifactAuditTests._write_csv(run_dir / "record_predictions.csv", predictions)
        metrics = [{
            "scenario_id": "s1",
            "method": "deterministic_policy_rules",
            "representation": "true_policy_checks",
            "operating_point": "rules_fixed",
            "evaluation_count": 2,
            "positive_count": 1,
            "negative_count": 1,
            "alert_count": 1,
            "true_positives": 1,
            "false_positives": 0,
            "true_negatives": 1,
            "false_negatives": 0,
            "precision": 1.0,
            "recall": 1.0,
            "f1": 1.0,
            "false_positive_rate": 0.0,
            "alert_rate": 0.5,
            "rare_legitimate_count": 0,
            "rare_legitimate_flagged": 0,
            "rare_legitimate_flagged_rate": 0.0,
            "ordinary_clean_count": 1,
            "ordinary_clean_flagged": 0,
            "ordinary_clean_flagged_rate": 0.0,
        }]
        ProtocolArtifactAuditTests._write_csv(run_dir / "scenario_metrics.csv", metrics)
        aggregate = [{
            "method": "deterministic_policy_rules",
            "representation": "true_policy_checks",
            "operating_point": "rules_fixed",
            "scenario_count": 1,
            **{f"{column}_total": metrics[0][column] for column in (
                "evaluation_count", "positive_count", "negative_count", "alert_count",
                "true_positives", "false_positives", "true_negatives", "false_negatives",
                "rare_legitimate_count", "rare_legitimate_flagged",
                "ordinary_clean_count", "ordinary_clean_flagged",
            )},
            **{f"{column}_mean": metrics[0][column] for column in (
                "precision", "recall", "f1", "false_positive_rate", "alert_rate",
                "rare_legitimate_flagged_rate", "ordinary_clean_flagged_rate",
            )},
            "average_precision_mean": 1.0,
        }]
        ProtocolArtifactAuditTests._write_csv(run_dir / "aggregate_metrics.csv", aggregate)
        for name in ("paired_comparisons.csv", "robustness_slices.csv", "scenario_configs.csv", "utility_sensitivity.csv"):
            (run_dir / name).write_text("fixture\n", encoding="utf-8")
        files = {
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in run_dir.iterdir()
            if path.is_file()
        }
        (run_dir / "manifest.json").write_text(
            json.dumps({"algorithm": "sha256", "files": files}, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
