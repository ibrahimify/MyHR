import csv
import json
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from scripts.audit_tdk_protocol_artifact import (
    ArtifactAuditError,
    PAIR_METRICS,
    _event_rows_sha256,
    _expected_metric_suffixes,
    _verify_declared_matrix,
    _verify_paired_comparisons,
    _verify_scenario_metrics,
    _verify_truth_sidecars,
    audit_artifact,
)
from scripts.run_tdk_protocol_experiment import _paired_comparisons
from scripts.run_tdk_research_experiment import PROVENANCE_SOURCE_PATHS


def _complete_source_hashes() -> dict:
    """Build the COMPLETE required source-hash map at HEAD.

    The artifact auditor now enforces that provenance covers every required
    source path (finding R10), so fixtures must supply the full set rather than
    a single stand-in file.
    """
    import subprocess

    repo_root = Path.cwd()
    hashes = {}
    for path in PROVENANCE_SOURCE_PATHS:
        content = subprocess.run(
            ["git", "show", f"HEAD:{path}"],
            cwd=repo_root, capture_output=True,
        ).stdout
        hashes[path] = sha256(content).hexdigest()
    return hashes


class ProtocolArtifactAuditTests(unittest.TestCase):
    def test_required_truth_sidecars_cannot_all_be_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ArtifactAuditError, "required truth sidecars"):
                _verify_truth_sidecars(Path(directory), [], required=True)

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

    def test_audit_recomputes_average_precision_from_scores(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            self._write_fixture(run_dir)
            with (run_dir / "record_predictions.csv").open(
                newline="", encoding="utf-8"
            ) as handle:
                predictions = list(csv.DictReader(handle))
            for row in predictions:
                row["score"] = "0.0"
            self._write_csv(run_dir / "record_predictions.csv", predictions)
            self._rewrite_manifest(run_dir)

            with self.assertRaisesRegex(ArtifactAuditError, "average_precision mismatch"):
                audit_artifact(run_dir, Path.cwd())

    def test_truth_sidecars_preserve_joinable_causal_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            ledger_event = {
                "scenario_id": "s1",
                "employee_id": "E1",
                "event_id": "EV-1",
                "event_kind": "promotion",
                "policy_id": "legacy-2018",
                "effective_date": "2022-01-01",
                "recorded_date": "2022-01-02",
                "approval_reference": "AR-1",
                "correction_of_event_id": "",
                "level_before": "L7",
                "level_after": "L6",
                "category": "",
                "resolved_date": "",
            }
            self._write_csv(run_dir / "record_truth.csv", [{
                "scenario_id": "s1",
                "employee_id": "E1",
                "split": "test",
                "truth_category": "rare_legitimate",
                "nominal_anomaly_mechanism": "approval_bypass",
                "nominal_rare_pattern": "grandfathered_policy",
                "realized_mechanism": "grandfathered_policy",
                "employment_track": "progression",
                "current_level": "L6",
                "department": "Operations",
                "role": "Officer",
                "date_of_birth": "1990-01-01",
                "hire_date": "2020-01-01",
                "event_count": 1,
                "event_ledger_sha256": _event_rows_sha256([ledger_event]),
                "causal_evidence": "Grandfathered service requirement.",
                "causal_events_json": json.dumps([{
                    "event_id": "EV-1",
                    "kind": "promotion",
                    "policy_id": "legacy-2018",
                    "effective_date": "2022-01-01",
                    "recorded_date": "2022-01-02",
                    "category": None,
                    "resolved_date": None,
                    "approval_reference": "AR-1",
                    "correction_of_event_id": None,
                    "level_before": "L7",
                    "level_after": "L6",
                    "ledger_status": "observed",
                }]),
            }])
            self._write_csv(run_dir / "administrative_events.csv", [ledger_event])
            self._write_csv(run_dir / "policy_epochs.csv", [{
                "scenario_id": "s1",
                "policy_id": "legacy-2018",
                "effective_from": "2018-01-01",
                "service_months_by_level_json": json.dumps({"L7": 30}),
                "grandfather_previous_policy": True,
            }])
            result = _verify_truth_sidecars(run_dir, [{
                "scenario_id": "s1",
                "employee_id": "E1",
            }])

            self.assertTrue(result["present"])
            self.assertEqual(result["record_truth_rows"], 1)

            with (run_dir / "record_truth.csv").open(
                newline="", encoding="utf-8"
            ) as handle:
                truth_rows = list(csv.DictReader(handle))
            causal = json.loads(truth_rows[0]["causal_events_json"])
            causal[0]["kind"] = "sanction"
            truth_rows[0]["causal_events_json"] = json.dumps(causal)
            self._write_csv(run_dir / "record_truth.csv", truth_rows)
            with self.assertRaisesRegex(ArtifactAuditError, "does not match event ledger"):
                _verify_truth_sidecars(run_dir, [{
                    "scenario_id": "s1",
                    "employee_id": "E1",
                }])

    def test_truth_sidecars_validate_omitted_causal_events(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            causal = {
                "event_id": "EV-REMOVED",
                "kind": "salary_increment",
                "policy_id": "legacy-2018",
                "effective_date": "2022-01-01",
                "recorded_date": "2022-01-02",
                "category": None,
                "resolved_date": None,
                "approval_reference": None,
                "correction_of_event_id": None,
                "level_before": None,
                "level_after": None,
                "ledger_status": "omitted",
            }
            ledger_event = {
                "scenario_id": "s1", "employee_id": "E1", "event_id": "EV-OBSERVED",
                "event_kind": "hire", "policy_id": "legacy-2018",
                "effective_date": "2020-01-01", "recorded_date": "2020-01-01",
                "approval_reference": "", "correction_of_event_id": "",
                "level_before": "", "level_after": "L7", "category": "",
                "resolved_date": "",
            }
            self._write_csv(run_dir / "record_truth.csv", [{
                "scenario_id": "s1", "employee_id": "E1", "split": "test",
                "truth_category": "confirmed_recording_error",
                "nominal_anomaly_mechanism": "missing_increment_import",
                "nominal_rare_pattern": "grandfathered_policy",
                "realized_mechanism": "missing_increment_import",
                "employment_track": "progression", "current_level": "L7",
                "department": "Operations", "role": "Officer",
                "date_of_birth": "1990-01-01", "hire_date": "2020-01-01",
                "event_count": 1,
                "event_ledger_sha256": _event_rows_sha256([ledger_event]),
                "causal_evidence": "omitted",
                "causal_events_json": json.dumps([causal]),
            }])
            self._write_csv(run_dir / "administrative_events.csv", [ledger_event])
            self._write_csv(run_dir / "policy_epochs.csv", [{
                "scenario_id": "s1", "policy_id": "legacy-2018",
                "effective_from": "2018-01-01",
                "service_months_by_level_json": json.dumps({"L7": 30}),
                "grandfather_previous_policy": True,
            }])
            prediction = [{"scenario_id": "s1", "employee_id": "E1"}]
            self.assertTrue(_verify_truth_sidecars(run_dir, prediction)["present"])

            changed_ledger = dict(ledger_event, event_kind="promotion")
            self._write_csv(run_dir / "administrative_events.csv", [changed_ledger])
            with self.assertRaisesRegex(ArtifactAuditError, "event ledger checksum mismatch"):
                _verify_truth_sidecars(run_dir, prediction)
            self._write_csv(run_dir / "administrative_events.csv", [ledger_event])

            causal["ledger_status"] = "observed"
            with (run_dir / "record_truth.csv").open(
                newline="", encoding="utf-8"
            ) as handle:
                rows = list(csv.DictReader(handle))
            rows[0]["causal_events_json"] = json.dumps([causal])
            self._write_csv(run_dir / "record_truth.csv", rows)
            with self.assertRaisesRegex(ArtifactAuditError, "missing from event ledger"):
                _verify_truth_sidecars(run_dir, prediction)

    def test_audit_recomputes_paired_inference_and_holm_values(self):
        metrics = []
        for scenario_index, scenario_id in enumerate(("s1", "s2"), start=1):
            for representation, offset in (("raw_matched", 0.0), ("policy_matched", 0.05)):
                row = {
                    "scenario_id": scenario_id,
                    "method": "isolation_forest_residual",
                    "representation": representation,
                    "operating_point": "fixed_review_budget",
                }
                for metric_index, metric in enumerate(PAIR_METRICS, start=1):
                    row[metric] = 0.1 * scenario_index + 0.001 * metric_index + offset
                metrics.append(row)
        paired = _paired_comparisons(metrics)

        self.assertEqual(paired[0]["scenario_count"], 2)
        self.assertAlmostEqual(paired[0]["average_precision_delta_mean"], 0.05)
        self.assertAlmostEqual(paired[0]["average_precision_delta_median"], 0.05)
        self.assertAlmostEqual(paired[0]["average_precision_delta_std"], 0.0)
        self.assertAlmostEqual(paired[0]["average_precision_delta_ci95_low"], 0.05)
        self.assertAlmostEqual(paired[0]["average_precision_delta_ci95_high"], 0.05)
        self.assertAlmostEqual(paired[0]["average_precision_delta_sign_flip_p"], 0.5)
        self.assertAlmostEqual(paired[0]["average_precision_delta_holm_all_p"], 1.0)
        _verify_paired_comparisons(metrics, paired)
        paired[0]["average_precision_delta_ci95_high"] = (
            float(paired[0]["average_precision_delta_ci95_high"]) + 0.1
        )
        with self.assertRaisesRegex(ArtifactAuditError, "paired .* mismatch"):
            _verify_paired_comparisons(metrics, paired)

    def test_audit_rejects_duplicate_metric_keys_and_incomplete_pairs(self):
        prediction = {
            "scenario_id": "s1", "employee_id": "E1", "method": "m",
            "representation": "raw_matched", "operating_point": "budget",
        }
        metric = {key: value for key, value in prediction.items() if key != "employee_id"}
        with self.assertRaisesRegex(ArtifactAuditError, "duplicate scenario metric"):
            _verify_scenario_metrics([metric, dict(metric)], [prediction])

        paired_metric = {
            "scenario_id": "s1", "method": "isolation_forest_residual",
            "representation": "raw_matched", "operating_point": "fixed_review_budget",
            **{name: 0.5 for name in PAIR_METRICS},
        }
        with self.assertRaisesRegex(ArtifactAuditError, "incomplete raw/policy pair"):
            _verify_paired_comparisons([paired_metric], [])

    def test_declared_matrix_rejects_coordinated_metric_group_deletion(self):
        protocol = "independent-development-v1-2026-10-16"
        expected = _expected_metric_suffixes(protocol)
        self.assertIsNotNone(expected)
        rows = [{
            "scenario_id": "s1", "method": method,
            "representation": representation, "operating_point": operating_point,
        } for method, representation, operating_point in expected]
        metadata = {"protocol_version": protocol, "scenario_count": 1}
        configs = [{"scenario_id": "s1"}]

        _verify_declared_matrix(metadata, configs, rows)
        with self.assertRaisesRegex(ArtifactAuditError, "metric matrix is incomplete"):
            _verify_declared_matrix(metadata, configs, rows[:-1])

    @staticmethod
    def _write_fixture(run_dir: Path) -> None:
        metadata = {
            "artifact_id": "fixture",
            "holdout_accessed": False,
            "protocol_status": "draft_validation_holdout_locked",
            "protocol_version": "fixture",
            "run_purpose": "validation",
            "scenario_count": 1,
            "provenance": {
                "git_commit": "HEAD",
                "git_dirty": False,
                "source_sha256": _complete_source_hashes(),
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
                "score": "1.0",
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
                "score": "0.0",
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
            "average_precision": 1.0,
            "anomalies_found_per_100_reviews": 100.0,
            "rare_legitimate_reviews_per_1000_employees": 0.0,
            "missed_anomalies_per_1000_employees": 0.0,
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
                "anomalies_found_per_100_reviews",
                "rare_legitimate_reviews_per_1000_employees",
                "missed_anomalies_per_1000_employees",
            )},
            "average_precision_mean": 1.0,
        }]
        ProtocolArtifactAuditTests._write_csv(run_dir / "aggregate_metrics.csv", aggregate)
        ProtocolArtifactAuditTests._write_csv(
            run_dir / "scenario_configs.csv", [{"scenario_id": "s1"}]
        )
        for name in ("paired_comparisons.csv", "robustness_slices.csv", "utility_sensitivity.csv"):
            (run_dir / name).write_text("fixture\n", encoding="utf-8")
        ProtocolArtifactAuditTests._rewrite_manifest(run_dir)

    @staticmethod
    def _rewrite_manifest(run_dir: Path) -> None:
        files = {
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in run_dir.iterdir()
            if path.is_file() and path.name != "manifest.json"
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
