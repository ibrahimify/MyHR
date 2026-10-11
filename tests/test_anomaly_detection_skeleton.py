import unittest
from datetime import date, datetime, timedelta

from src.services.anomaly_detection import (
    AdministrativeEvent,
    AdministrativeEventType,
    AnomalyType,
    DatasetSplit,
    EmployeeIdentity,
    EmploymentTrack,
    ExperimentConfig,
    PromotionPolicy,
    ValidationSeverity,
    WorkforceHistoryRecord,
    anomaly_taxonomy,
    confusion_counts,
    generate_synthetic_dataset,
    serialize_dataset,
    split_indices,
    summarize_findings,
    validate_dataset,
    validate_record,
)
from src.services.anomaly_detection.deterministic_checks import date_is_not_after, has_duplicate_identifier
from src.services.anomaly_detection.duplicate_detection import normalized_similarity
from src.services.anomaly_detection.experiment_runner import describe_experiment
from src.services.anomaly_detection.features import supported_feature_sets


class AnomalyDetectionSkeletonTests(unittest.TestCase):
    def test_experiment_config_has_stable_run_id(self):
        first = ExperimentConfig(seed=42, employee_count=100)
        second = ExperimentConfig(seed=42, employee_count=100)

        self.assertEqual(first.run_id(), second.run_id())
        self.assertEqual(describe_experiment(first)["run_id"], first.run_id())

    def test_split_indices_are_deterministic_and_complete(self):
        config = ExperimentConfig(seed=7, employee_count=10)

        first = split_indices(10, config)
        second = split_indices(10, config)

        self.assertEqual(first, second)
        combined = first["train"] + first["validation"] + first["test"]
        self.assertEqual(sorted(combined), list(range(10)))
        self.assertEqual(len(set(combined)), 10)

    def test_invalid_split_ratios_are_rejected(self):
        config = ExperimentConfig(train_ratio=0.7, validation_ratio=0.2, test_ratio=0.2)

        with self.assertRaises(ValueError):
            config.validate()

    def test_policy_model_keeps_other_track_out_of_promotion_race(self):
        policy = PromotionPolicy()

        self.assertTrue(policy.is_promotion_track("L7"))
        self.assertFalse(policy.is_promotion_track("Other"))
        self.assertEqual(policy.required_service_months("L7"), 36)
        self.assertIsNone(policy.required_service_months("Other"))

    def test_confusion_metrics_are_computed_without_majority_voting(self):
        metrics = confusion_counts(
            y_true=[True, True, False, False],
            y_pred=[True, False, True, False],
        )

        self.assertEqual(metrics.true_positives, 1)
        self.assertEqual(metrics.false_positives, 1)
        self.assertEqual(metrics.true_negatives, 1)
        self.assertEqual(metrics.false_negatives, 1)
        self.assertAlmostEqual(metrics.precision, 0.5)
        self.assertAlmostEqual(metrics.recall, 0.5)
        self.assertAlmostEqual(metrics.f1, 0.5)
        self.assertAlmostEqual(metrics.false_positive_rate, 0.5)

    def test_deterministic_checks_are_side_effect_limited(self):
        now = datetime(2026, 1, 1)

        self.assertTrue(date_is_not_after(now, now + timedelta(days=1)))
        self.assertFalse(date_is_not_after(now + timedelta(days=1), now))

        seen = set()
        self.assertFalse(has_duplicate_identifier("EMP-001", seen))
        self.assertTrue(has_duplicate_identifier(" emp-001 ", seen))

    def test_duplicate_similarity_is_normalized(self):
        self.assertEqual(normalized_similarity("Ibrahim", "ibrahim"), 1.0)
        self.assertGreater(normalized_similarity("Ibrahim", "Ibrahim Shoeb"), 0.6)

    def test_declares_raw_and_policy_aware_feature_sets(self):
        self.assertEqual(supported_feature_sets(), ("raw", "policy_aware"))

    def test_anomaly_taxonomy_documents_clean_errors_and_rare_legitimate_cases(self):
        taxonomy = anomaly_taxonomy()
        anomaly_types = {entry.anomaly_type for entry in taxonomy}

        self.assertIn(AnomalyType.CLEAN, anomaly_types)
        self.assertIn(AnomalyType.INCONSISTENT_DATES, anomaly_types)
        self.assertIn(AnomalyType.FREQUENT_PROMOTIONS, anomaly_types)
        self.assertIn(AnomalyType.EXCESSIVE_SANCTIONS, anomaly_types)
        self.assertIn(AnomalyType.DUPLICATE_RECORD, anomaly_types)
        self.assertIn(AnomalyType.UNUSUAL_ADMIN_INTERVAL, anomaly_types)
        self.assertIn(AnomalyType.POLICY_LEGITIMATE_RARE_CASE, anomaly_types)

        rare_case = next(entry for entry in taxonomy if entry.anomaly_type is AnomalyType.POLICY_LEGITIMATE_RARE_CASE)
        self.assertFalse(rare_case.ground_truth_label)
        self.assertIn("policy-aware", rare_case.expected_signal)

    def test_workforce_history_record_marks_legitimate_rare_case_as_non_anomalous(self):
        record = WorkforceHistoryRecord(
            identity=EmployeeIdentity(
                employee_id="EMP-1052",
                full_name="Ibrahim Shoeb",
                date_of_birth=date(1985, 3, 12),
            ),
            split=DatasetSplit.TEST,
            employment_track=EmploymentTrack.PROMOTION,
            current_level="L5",
            department="Engineering",
            role="Software Engineer",
            hire_date=date(2020, 1, 1),
            events=(
                AdministrativeEvent(
                    event_type=AdministrativeEventType.COMMENDATION,
                    event_date=date(2023, 6, 1),
                    source_id="COM-1",
                    category=2,
                ),
            ),
            anomaly_labels=(AnomalyType.POLICY_LEGITIMATE_RARE_CASE,),
        )

        self.assertFalse(record.has_anomaly)

    def test_workforce_history_record_marks_injected_error_as_anomalous(self):
        record = WorkforceHistoryRecord(
            identity=EmployeeIdentity(
                employee_id="EMP-1258",
                full_name="Ibrahim",
                date_of_birth=date(1985, 3, 12),
            ),
            split=DatasetSplit.VALIDATION,
            employment_track=EmploymentTrack.PROMOTION,
            current_level="L6",
            department="Operations",
            role="Officer",
            hire_date=date(2024, 1, 1),
            events=(
                AdministrativeEvent(
                    event_type=AdministrativeEventType.PROMOTION,
                    event_date=date(2023, 1, 1),
                    source_id="PROM-1",
                    level_before="L7",
                    level_after="L6",
                ),
            ),
            anomaly_labels=(AnomalyType.INCONSISTENT_DATES,),
        )

        self.assertTrue(record.has_anomaly)

    def test_synthetic_dataset_generation_is_reproducible(self):
        config = ExperimentConfig(seed=99, employee_count=40, anomaly_rate=0.10, rare_legitimate_rate=0.05)

        first = serialize_dataset(generate_synthetic_dataset(config))
        second = serialize_dataset(generate_synthetic_dataset(config))

        self.assertEqual(first, second)
        self.assertEqual(first["metadata"]["run_id"], config.run_id())
        self.assertEqual(first["metadata"]["employee_count"], 40)

    def test_synthetic_dataset_metadata_tracks_splits_and_labels(self):
        config = ExperimentConfig(seed=123, employee_count=50, anomaly_rate=0.10, rare_legitimate_rate=0.04)
        dataset = generate_synthetic_dataset(config)

        self.assertEqual(len(dataset.records), 50)
        self.assertEqual(sum(dataset.metadata.split_counts.values()), 50)
        self.assertEqual(dataset.metadata.split_counts["train"], 30)
        self.assertEqual(dataset.metadata.split_counts["validation"], 10)
        self.assertEqual(dataset.metadata.split_counts["test"], 10)

        true_anomaly_count = sum(record.has_anomaly for record in dataset.records)
        self.assertEqual(true_anomaly_count, 5)
        self.assertEqual(dataset.metadata.label_counts[AnomalyType.POLICY_LEGITIMATE_RARE_CASE.value], 2)

    def test_synthetic_dataset_duplicate_records_keep_source_link(self):
        config = ExperimentConfig(seed=2026, employee_count=80, anomaly_rate=0.15, rare_legitimate_rate=0.02)
        dataset = generate_synthetic_dataset(config)

        duplicates = [
            record for record in dataset.records
            if AnomalyType.DUPLICATE_RECORD in record.anomaly_labels
        ]

        self.assertGreaterEqual(len(duplicates), 1)
        self.assertTrue(all(record.duplicate_of_employee_id for record in duplicates))
        source_ids = {record.identity.employee_id for record in dataset.records}
        self.assertTrue(all(record.duplicate_of_employee_id in source_ids for record in duplicates))

    def test_deterministic_validation_explains_inconsistent_dates(self):
        record = WorkforceHistoryRecord(
            identity=EmployeeIdentity(
                employee_id="EMP-9001",
                full_name="Date Broken",
                date_of_birth=date(1990, 1, 1),
            ),
            split=DatasetSplit.TEST,
            employment_track=EmploymentTrack.PROMOTION,
            current_level="L6",
            department="Operations",
            role="Officer",
            hire_date=date(2024, 1, 1),
            events=(
                AdministrativeEvent(
                    event_type=AdministrativeEventType.HIRE,
                    event_date=date(2024, 1, 1),
                    source_id="HIRE-9001",
                ),
                AdministrativeEvent(
                    event_type=AdministrativeEventType.PROMOTION,
                    event_date=date(2023, 1, 1),
                    source_id="PROM-BEFORE-HIRE",
                    level_before="L7",
                    level_after="L6",
                ),
            ),
        )

        findings = validate_record(record)

        self.assertEqual(findings[0].severity, ValidationSeverity.ERROR)
        self.assertIn("event_before_hire_date", {finding.code for finding in findings})
        self.assertTrue(any(finding.event_source_id == "PROM-BEFORE-HIRE" for finding in findings))

    def test_deterministic_validation_flags_short_promotion_and_increment_intervals(self):
        config = ExperimentConfig(seed=2026, employee_count=80, anomaly_rate=0.15, rare_legitimate_rate=0.02)
        dataset = generate_synthetic_dataset(config)
        findings = validate_dataset(dataset)
        summary = summarize_findings(findings)

        self.assertGreaterEqual(summary.get("promotion_interval_too_short", 0), 1)
        self.assertGreaterEqual(summary.get("salary_increment_interval_too_short", 0), 1)

    def test_deterministic_validation_does_not_flag_clean_records(self):
        config = ExperimentConfig(seed=5, employee_count=20, anomaly_rate=0.0, rare_legitimate_rate=0.0)
        dataset = generate_synthetic_dataset(config)

        findings = validate_dataset(dataset)

        self.assertEqual(findings, ())


if __name__ == "__main__":
    unittest.main()
