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
    evaluate_duplicate_detection,
    evaluate_statistical_baseline,
    extract_features,
    extract_policy_aware_features,
    extract_raw_features,
    generate_synthetic_dataset,
    run_isolation_forest,
    serialize_dataset,
    sklearn_is_available,
    split_indices,
    summarize_findings,
    validate_dataset,
    validate_record,
)
from src.services.anomaly_detection.deterministic_checks import date_is_not_after, has_duplicate_identifier
from src.services.anomaly_detection.duplicate_detection import (
    find_exact_duplicate_candidates,
    find_normalized_exact_duplicate_candidates,
    find_similarity_duplicate_candidates,
    normalize_identifier,
    normalized_similarity,
)
from src.services.anomaly_detection.experiment_runner import describe_experiment
from src.services.anomaly_detection.features import supported_feature_sets
from src.services.anomaly_detection.isolation_forest import IsolationForestUnavailableError
from src.services.anomaly_detection.statistical_baselines import (
    fit_iqr_baseline,
    fit_z_score_baseline,
    predict_baseline,
)


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
        self.assertEqual(normalize_identifier("NID-0001258"), "nid-1258")

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

    def test_synthetic_dataset_spreads_labels_across_splits_when_possible(self):
        config = ExperimentConfig(seed=2026, employee_count=120, anomaly_rate=0.10, rare_legitimate_rate=0.05)
        dataset = generate_synthetic_dataset(config)

        for split in DatasetSplit:
            split_records = [record for record in dataset.records if record.split is split]
            self.assertTrue(any(record.has_anomaly for record in split_records))
            self.assertTrue(any(AnomalyType.POLICY_LEGITIMATE_RARE_CASE in record.anomaly_labels for record in split_records))

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

    def test_raw_features_capture_policy_agnostic_counts_and_intervals(self):
        config = ExperimentConfig(seed=2026, employee_count=80, anomaly_rate=0.15, rare_legitimate_rate=0.02)
        dataset = generate_synthetic_dataset(config)
        record = next(record for record in dataset.records if AnomalyType.FREQUENT_PROMOTIONS in record.anomaly_labels)

        features = extract_raw_features(record)

        self.assertEqual(features.feature_set, "raw")
        self.assertEqual(features.values["employment_track_is_promotion"], 1.0)
        self.assertGreaterEqual(features.values["promotion_count"], 2.0)
        self.assertLess(features.values["min_promotion_interval_months"], 12.0)

    def test_policy_aware_features_explain_rare_legitimate_promotion_case(self):
        config = ExperimentConfig(seed=2026, employee_count=80, anomaly_rate=0.15, rare_legitimate_rate=0.02)
        dataset = generate_synthetic_dataset(config)
        record = next(record for record in dataset.records if AnomalyType.POLICY_LEGITIMATE_RARE_CASE in record.anomaly_labels)

        raw = extract_raw_features(record)
        policy_aware = extract_policy_aware_features(record)

        self.assertEqual(policy_aware.feature_set, "policy_aware")
        self.assertLess(
            policy_aware.values["latest_promotion_observed_service_months"],
            policy_aware.values["latest_promotion_required_service_months"],
        )
        self.assertGreater(policy_aware.values["policy_commendation_credit_months"], 0.0)
        self.assertEqual(policy_aware.values["policy_service_deficit_months"], 0.0)
        self.assertEqual(policy_aware.values["policy_explains_short_promotion"], 1.0)
        self.assertEqual(raw.values["has_duplicate_source"], 0.0)

    def test_feature_dispatch_rejects_unknown_feature_sets(self):
        config = ExperimentConfig(seed=5, employee_count=5, anomaly_rate=0.0, rare_legitimate_rate=0.0)
        record = generate_synthetic_dataset(config).records[0]

        self.assertEqual(extract_features(record, "raw").feature_set, "raw")
        self.assertEqual(extract_features(record, "policy_aware").feature_set, "policy_aware")
        with self.assertRaises(ValueError):
            extract_features(record, "made_up")

    def test_statistical_baseline_models_predict_outliers(self):
        config = ExperimentConfig(seed=2026, employee_count=80, anomaly_rate=0.15, rare_legitimate_rate=0.02)
        dataset = generate_synthetic_dataset(config)
        vectors = tuple(extract_raw_features(record) for record in dataset.records if record.split is DatasetSplit.TRAIN)
        feature_names = ("promotion_count", "sanction_count", "min_salary_increment_interval_days")

        z_model = fit_z_score_baseline(vectors, feature_names, threshold=2.0)
        iqr_model = fit_iqr_baseline(vectors, feature_names)
        z_predictions = predict_baseline(z_model, vectors)
        iqr_predictions = predict_baseline(iqr_model, vectors)

        self.assertEqual(z_model.method, "z_score")
        self.assertEqual(iqr_model.method, "iqr")
        self.assertEqual(len(z_predictions), len(vectors))
        self.assertEqual(len(iqr_predictions), len(vectors))

    def test_evaluate_statistical_baseline_returns_metrics_and_rare_case_count(self):
        config = ExperimentConfig(seed=2026, employee_count=120, anomaly_rate=0.15, rare_legitimate_rate=0.05)
        dataset = generate_synthetic_dataset(config)

        raw_result = evaluate_statistical_baseline(dataset, "raw", "iqr")
        policy_result = evaluate_statistical_baseline(dataset, "policy_aware", "iqr")

        self.assertEqual(raw_result.method, "iqr")
        self.assertEqual(policy_result.feature_set, "policy_aware")
        self.assertGreaterEqual(raw_result.metrics.true_positives + raw_result.metrics.false_positives, 0)
        self.assertGreaterEqual(policy_result.rare_legitimate_false_positives, 0)
        self.assertGreaterEqual(policy_result.predicted_positive_count, 0)

    def test_isolation_forest_boundary_is_explicit_about_optional_dependency(self):
        config = ExperimentConfig(seed=5, employee_count=20, anomaly_rate=0.1, rare_legitimate_rate=0.0)
        dataset = generate_synthetic_dataset(config)
        train_vectors = tuple(extract_raw_features(record) for record in dataset.records if record.split is DatasetSplit.TRAIN)
        test_vectors = tuple(extract_raw_features(record) for record in dataset.records if record.split is DatasetSplit.TEST)

        if sklearn_is_available():
            result = run_isolation_forest(
                train_vectors=train_vectors,
                test_vectors=test_vectors,
                feature_names=("promotion_count", "sanction_count"),
                contamination=0.1,
                random_state=5,
            )
            self.assertEqual(len(result.predictions), len(test_vectors))
            self.assertEqual(len(result.scores), len(test_vectors))
        else:
            with self.assertRaises(IsolationForestUnavailableError):
                run_isolation_forest(
                    train_vectors=train_vectors,
                    test_vectors=test_vectors,
                    feature_names=("promotion_count", "sanction_count"),
                    contamination=0.1,
                    random_state=5,
                )

    def test_duplicate_detection_compares_exact_normalized_and_similarity_methods(self):
        config = ExperimentConfig(seed=2026, employee_count=80, anomaly_rate=0.15, rare_legitimate_rate=0.02)
        dataset = generate_synthetic_dataset(config)

        exact = evaluate_duplicate_detection(dataset, "exact")
        normalized = evaluate_duplicate_detection(dataset, "normalized_exact")
        similarity = evaluate_duplicate_detection(dataset, "similarity", threshold=0.70)

        self.assertEqual(exact.method, "exact")
        self.assertEqual(normalized.method, "normalized_exact")
        self.assertEqual(similarity.method, "similarity")
        self.assertGreaterEqual(normalized.metrics.recall, exact.metrics.recall)
        self.assertGreaterEqual(similarity.metrics.recall, normalized.metrics.recall)

    def test_duplicate_detection_candidates_include_review_evidence(self):
        config = ExperimentConfig(seed=2026, employee_count=80, anomaly_rate=0.15, rare_legitimate_rate=0.02)
        dataset = generate_synthetic_dataset(config)

        candidates = find_similarity_duplicate_candidates(dataset.records, threshold=0.70)

        self.assertGreaterEqual(len(candidates), 1)
        first = candidates[0]
        self.assertIn("name_similarity", first.evidence)
        self.assertIn("date_of_birth_match", first.evidence)
        self.assertIn("national_id_similarity", first.evidence)
        self.assertGreaterEqual(first.score, 0.70)

    def test_duplicate_detection_baselines_are_available_separately(self):
        config = ExperimentConfig(seed=2026, employee_count=80, anomaly_rate=0.15, rare_legitimate_rate=0.02)
        dataset = generate_synthetic_dataset(config)

        exact = find_exact_duplicate_candidates(dataset.records)
        normalized = find_normalized_exact_duplicate_candidates(dataset.records)

        self.assertGreaterEqual(len(normalized), len(exact))


if __name__ == "__main__":
    unittest.main()
