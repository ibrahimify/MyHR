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
    HardNonduplicateKind,
    LatentPerson,
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
    select_similarity_threshold,
)
from src.services.anomaly_detection.experiment_runner import DEFAULT_POLICY_AWARE_FEATURES, describe_experiment
from src.services.anomaly_detection.features import supported_feature_sets
from src.services.anomaly_detection.isolation_forest import IsolationForestUnavailableError
from src.services.anomaly_detection.statistical_baselines import (
    fit_iqr_baseline,
    fit_z_score_baseline,
    predict_baseline,
)
from scripts.run_tdk_research_multiseed import _bootstrap_mean_ci, _paired_sign_flip_pvalue


class AnomalyDetectionSkeletonTests(unittest.TestCase):
    def test_paired_uncertainty_helpers_are_deterministic(self):
        values = [-1.0, -1.0, -1.0, -1.0, -1.0]

        first_interval = _bootstrap_mean_ci(values, seed=20261015, samples=1000)
        second_interval = _bootstrap_mean_ci(values, seed=20261015, samples=1000)

        self.assertEqual(first_interval, second_interval)
        self.assertEqual(first_interval, (-1.0, -1.0))
        self.assertEqual(_paired_sign_flip_pvalue(values, seed=20261015), 0.0625)

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
        self.assertTrue(all(record.has_anomaly for record in duplicates))
        self.assertTrue(all(not record.has_progression_anomaly for record in duplicates))
        source_ids = {record.identity.employee_id for record in dataset.records}
        self.assertTrue(all(record.duplicate_of_employee_id in source_ids for record in duplicates))

    def test_synthetic_dataset_spreads_labels_across_splits_when_possible(self):
        config = ExperimentConfig(seed=2026, employee_count=120, anomaly_rate=0.10, rare_legitimate_rate=0.05)
        dataset = generate_synthetic_dataset(config)

        for split in DatasetSplit:
            split_records = [record for record in dataset.records if record.split is split]
            self.assertTrue(any(record.has_anomaly for record in split_records))
            self.assertTrue(any(AnomalyType.POLICY_LEGITIMATE_RARE_CASE in record.anomaly_labels for record in split_records))

    def test_rare_legitimate_promotions_only_use_promotion_track(self):
        config = ExperimentConfig(seed=2026, employee_count=1000, anomaly_rate=0.10, rare_legitimate_rate=0.05)
        dataset = generate_synthetic_dataset(config)
        rare_records = [
            record for record in dataset.records
            if AnomalyType.POLICY_LEGITIMATE_RARE_CASE in record.anomaly_labels
        ]

        self.assertEqual(len(rare_records), 50)
        self.assertTrue(all(record.employment_track is EmploymentTrack.PROMOTION for record in rare_records))
        rare_ids = {record.identity.employee_id for record in rare_records}
        rare_findings = [finding for finding in validate_dataset(dataset) if finding.employee_id in rare_ids]
        self.assertEqual(rare_findings, [])

    def test_clean_and_rare_histories_have_no_policy_service_deficit(self):
        config = ExperimentConfig(seed=2026, employee_count=1000, anomaly_rate=0.10, rare_legitimate_rate=0.05)
        dataset = generate_synthetic_dataset(config)
        expected_valid = [record for record in dataset.records if not record.has_anomaly]

        deficits = {
            record.identity.employee_id: extract_policy_aware_features(record).values["policy_service_deficit_months"]
            for record in expected_valid
        }

        self.assertTrue(all(deficit == 0.0 for deficit in deficits.values()))

    def test_synthetic_dataset_distributes_labels_proportionally_across_splits(self):
        config = ExperimentConfig(seed=2026, employee_count=1000, anomaly_rate=0.10, rare_legitimate_rate=0.05)
        dataset = generate_synthetic_dataset(config)

        records_by_split = {
            split: [record for record in dataset.records if record.split is split]
            for split in DatasetSplit
        }

        self.assertEqual(sum(record.has_anomaly for record in records_by_split[DatasetSplit.TRAIN]), 60)
        self.assertEqual(sum(record.has_anomaly for record in records_by_split[DatasetSplit.VALIDATION]), 20)
        self.assertEqual(sum(record.has_anomaly for record in records_by_split[DatasetSplit.TEST]), 20)
        self.assertEqual(
            sum(AnomalyType.POLICY_LEGITIMATE_RARE_CASE in record.anomaly_labels for record in records_by_split[DatasetSplit.TRAIN]),
            30,
        )
        self.assertEqual(
            sum(AnomalyType.POLICY_LEGITIMATE_RARE_CASE in record.anomaly_labels for record in records_by_split[DatasetSplit.VALIDATION]),
            10,
        )
        self.assertEqual(
            sum(AnomalyType.POLICY_LEGITIMATE_RARE_CASE in record.anomaly_labels for record in records_by_split[DatasetSplit.TEST]),
            10,
        )

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
        self.assertEqual(policy_aware.values["policy_service_deficit_ratio"], 0.0)
        self.assertEqual(policy_aware.values["policy_unexplained_short_promotion"], 0.0)
        self.assertEqual(policy_aware.values["policy_explains_short_promotion"], 1.0)
        self.assertNotIn("has_duplicate_source", raw.values)

    def test_policy_aware_experiment_features_use_policy_residuals(self):
        self.assertIn("policy_service_deficit_months", DEFAULT_POLICY_AWARE_FEATURES)
        self.assertIn("policy_service_deficit_ratio", DEFAULT_POLICY_AWARE_FEATURES)
        self.assertIn("policy_unexplained_short_promotion", DEFAULT_POLICY_AWARE_FEATURES)
        self.assertNotIn("min_promotion_interval_months", DEFAULT_POLICY_AWARE_FEATURES)
        self.assertNotIn("policy_explains_short_promotion", DEFAULT_POLICY_AWARE_FEATURES)

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
        progression_test_records = [
            record for record in dataset.records
            if record.split is DatasetSplit.TEST
            and AnomalyType.DUPLICATE_RECORD not in record.anomaly_labels
        ]

        self.assertEqual(raw_result.method, "iqr")
        self.assertEqual(policy_result.feature_set, "policy_aware")
        self.assertEqual(raw_result.evaluation_count, len(progression_test_records))
        self.assertEqual(
            raw_result.ground_truth_positive_count + raw_result.ground_truth_negative_count,
            raw_result.evaluation_count,
        )
        self.assertEqual(
            raw_result.rare_legitimate_count,
            sum(AnomalyType.POLICY_LEGITIMATE_RARE_CASE in record.anomaly_labels for record in progression_test_records),
        )
        self.assertEqual(raw_result.clean_count, sum(AnomalyType.CLEAN in record.anomaly_labels for record in progression_test_records))
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

    def test_duplicate_ground_truth_includes_sibling_pairs(self):
        config = ExperimentConfig(seed=2027, employee_count=1000, anomaly_rate=0.10, rare_legitimate_rate=0.05)
        dataset = generate_synthetic_dataset(config)

        normalized = evaluate_duplicate_detection(dataset, "normalized_exact")
        direct_test_links = sum(
            record.split is DatasetSplit.TEST
            and record.duplicate_of_employee_id is not None
            for record in dataset.records
        )

        self.assertGreaterEqual(normalized.true_pair_count, direct_test_links)
        self.assertEqual(
            normalized.metrics.true_positives + normalized.metrics.false_negatives,
            normalized.true_pair_count,
        )

    def test_duplicate_entities_never_cross_dataset_partitions(self):
        dataset = generate_synthetic_dataset(ExperimentConfig(
            seed=2026,
            employee_count=1000,
            anomaly_rate=0.10,
            rare_legitimate_rate=0.05,
        ))
        records = {record.identity.employee_id: record for record in dataset.records}

        for record in dataset.records:
            if record.duplicate_of_employee_id is not None:
                self.assertEqual(record.split, records[record.duplicate_of_employee_id].split)

    def test_missing_identity_values_do_not_create_similarity_evidence(self):
        self.assertEqual(normalized_similarity("", ""), 0.0)
        self.assertEqual(normalized_similarity("known", ""), 0.0)

    def test_similarity_default_matches_current_protocol_threshold(self):
        self.assertEqual(find_similarity_duplicate_candidates.__defaults__, (0.70,))

    def test_duplicate_threshold_is_selected_on_validation_and_scored_on_test(self):
        dataset = generate_synthetic_dataset(ExperimentConfig(
            seed=2026,
            employee_count=1000,
            anomaly_rate=0.10,
            rare_legitimate_rate=0.05,
        ))

        threshold = select_similarity_threshold(dataset)
        evaluation = evaluate_duplicate_detection(
            dataset, "similarity", threshold=threshold
        )

        self.assertEqual(evaluation.partition, DatasetSplit.TEST.value)
        self.assertGreater(evaluation.record_count, 0)
        self.assertLess(evaluation.record_count, len(dataset.records))
        self.assertGreaterEqual(evaluation.blocking_recall, 0.0)
        self.assertLessEqual(evaluation.blocking_recall, 1.0)
        self.assertGreaterEqual(evaluation.reduction_ratio, 0.0)
        self.assertLessEqual(evaluation.reduction_ratio, 1.0)


class LatentPersonFirstDuplicateTests(unittest.TestCase):
    """Verify latent-person-first duplicate generation contracts."""

    def _dataset(self, seed: int = 2026, count: int = 200) -> object:
        config = ExperimentConfig(seed=seed, employee_count=count, anomaly_rate=0.10, rare_legitimate_rate=0.02)
        from src.services.anomaly_detection import generate_synthetic_dataset
        return generate_synthetic_dataset(config)

    def test_duplicate_records_carry_latent_person_id(self):
        dataset = self._dataset()
        duplicates = [
            r for r in dataset.records
            if AnomalyType.DUPLICATE_RECORD in r.anomaly_labels
        ]
        self.assertGreaterEqual(len(duplicates), 1, "need at least one duplicate")
        for r in duplicates:
            self.assertIsNotNone(r.latent_person_id, f"duplicate {r.identity.employee_id} missing latent_person_id")
            self.assertTrue(r.latent_person_id.startswith("LP-"), f"unexpected latent_person_id format: {r.latent_person_id}")

    def test_source_records_also_carry_latent_person_id(self):
        """The source record of each cluster must also be tagged."""
        dataset = self._dataset()
        duplicates = [
            r for r in dataset.records
            if AnomalyType.DUPLICATE_RECORD in r.anomaly_labels
        ]
        source_ids = {r.duplicate_of_employee_id for r in duplicates if r.duplicate_of_employee_id}
        records_by_id = {r.identity.employee_id: r for r in dataset.records}
        for src_id in source_ids:
            src = records_by_id[src_id]
            self.assertIsNotNone(src.latent_person_id, f"source record {src_id} missing latent_person_id")

    def test_cluster_members_share_latent_person_id(self):
        """Each duplicate and its source must share the same latent_person_id."""
        dataset = self._dataset()
        records_by_id = {r.identity.employee_id: r for r in dataset.records}
        for r in dataset.records:
            if AnomalyType.DUPLICATE_RECORD in r.anomaly_labels:
                src = records_by_id.get(r.duplicate_of_employee_id)
                self.assertIsNotNone(src, f"source {r.duplicate_of_employee_id} not found")
                self.assertEqual(
                    r.latent_person_id,
                    src.latent_person_id,
                    f"duplicate {r.identity.employee_id} and source {src.identity.employee_id} "
                    f"disagree on latent_person_id",
                )

    def test_latent_person_id_format_is_stable_across_seeds(self):
        """LP-NNNNNN format must hold for multiple seeds."""
        import re
        pattern = re.compile(r"^LP-\d{6}$")
        for seed in (2026, 2027, 2028):
            dataset = self._dataset(seed=seed, count=300)
            for r in dataset.records:
                if r.latent_person_id is not None:
                    self.assertRegex(r.latent_person_id, pattern, f"seed {seed}: bad format {r.latent_person_id}")

    def test_partition_containment_enforced_by_construction(self):
        """Duplicate-cluster membership must never cross partitions (construction check)."""
        dataset = self._dataset(count=500)
        records_by_id = {r.identity.employee_id: r for r in dataset.records}
        for r in dataset.records:
            if AnomalyType.DUPLICATE_RECORD in r.anomaly_labels:
                src = records_by_id[r.duplicate_of_employee_id]
                self.assertEqual(
                    r.split, src.split,
                    f"partition violation: duplicate {r.identity.employee_id} in {r.split.value} "
                    f"but source {src.identity.employee_id} in {src.split.value}",
                )

    def test_non_duplicate_records_have_no_latent_person_id_unless_source(self):
        """Only cluster members (source + variants) should carry a latent_person_id."""
        dataset = self._dataset(count=500)
        cluster_ids: set[str] = set()
        for r in dataset.records:
            if AnomalyType.DUPLICATE_RECORD in r.anomaly_labels:
                cluster_ids.add(r.identity.employee_id)
                if r.duplicate_of_employee_id:
                    cluster_ids.add(r.duplicate_of_employee_id)
        for r in dataset.records:
            if r.identity.employee_id not in cluster_ids:
                self.assertIsNone(
                    r.latent_person_id,
                    f"unexpected latent_person_id on non-cluster record {r.identity.employee_id}",
                )


class HardNonduplicateTests(unittest.TestCase):
    """Verify explicit hard nonduplicate generation."""

    def _dataset(self, seed: int = 2026, count: int = 500) -> object:
        config = ExperimentConfig(seed=seed, employee_count=count, anomaly_rate=0.08, rare_legitimate_rate=0.02)
        from src.services.anomaly_detection import generate_synthetic_dataset
        return generate_synthetic_dataset(config)

    def test_all_hard_nonduplicate_kinds_are_present(self):
        dataset = self._dataset()
        found_kinds = {
            r.hard_nonduplicate_kind
            for r in dataset.records
            if r.hard_nonduplicate_kind is not None
        }
        for kind in HardNonduplicateKind:
            self.assertIn(kind, found_kinds, f"HardNonduplicateKind.{kind.name} not generated")

    def test_hard_nonduplicates_are_not_true_duplicates(self):
        """Hard nonduplicates must not appear in _true_duplicate_pairs."""
        from src.services.anomaly_detection.duplicate_detection import _true_duplicate_pairs
        dataset = self._dataset()
        records = tuple(r for r in dataset.records if r.split is DatasetSplit.TEST)
        true_pairs = _true_duplicate_pairs(records)
        hard_ids = {
            r.identity.employee_id
            for r in dataset.records
            if r.hard_nonduplicate_kind is not None
        }
        for left_id, right_id in true_pairs:
            self.assertNotIn(left_id, hard_ids, f"hard nonduplicate {left_id} appeared in true_pairs")
            self.assertNotIn(right_id, hard_ids, f"hard nonduplicate {right_id} appeared in true_pairs")

    def test_hard_nonduplicates_are_labelled_clean(self):
        """Hard nonduplicates are distinct genuine records — no DUPLICATE_RECORD label."""
        dataset = self._dataset()
        for r in dataset.records:
            if r.hard_nonduplicate_kind is not None:
                self.assertNotIn(
                    AnomalyType.DUPLICATE_RECORD,
                    r.anomaly_labels,
                    f"hard nonduplicate {r.identity.employee_id} incorrectly labelled DUPLICATE_RECORD",
                )
                self.assertIsNone(
                    r.duplicate_of_employee_id,
                    f"hard nonduplicate {r.identity.employee_id} has duplicate_of pointer",
                )

    def test_hard_nonduplicates_share_surface_feature_with_anchor(self):
        """Each hard nonduplicate kind should produce a confusable surface similarity."""
        from src.services.anomaly_detection.duplicate_detection import normalized_similarity
        dataset = self._dataset(count=800)
        hard_records = [r for r in dataset.records if r.hard_nonduplicate_kind is not None]
        clean_records = {
            r.identity.employee_id: r
            for r in dataset.records
            if r.anomaly_labels == (AnomalyType.CLEAN,) and r.hard_nonduplicate_kind is None
        }
        # At least one hard nonduplicate per kind should score >= 0.20 on name similarity
        # with some clean record in the dataset (the surface feature is present).
        for kind in HardNonduplicateKind:
            kind_records = [r for r in hard_records if r.hard_nonduplicate_kind is kind]
            if not kind_records:
                continue
            found_confusable = False
            for hnd in kind_records:
                for clean in list(clean_records.values())[:50]:
                    name_sim = normalized_similarity(
                        hnd.identity.full_name, clean.identity.full_name
                    )
                    dob_match = hnd.identity.date_of_birth == clean.identity.date_of_birth
                    id_sim = normalized_similarity(
                        hnd.identity.national_id or "", clean.identity.national_id or ""
                    )
                    if name_sim >= 0.30 or dob_match or id_sim >= 0.70:
                        found_confusable = True
                        break
                if found_confusable:
                    break
            self.assertTrue(found_confusable, f"HardNonduplicateKind.{kind.name}: no confusable surface similarity found")

    def test_hard_nonduplicate_count_is_bounded(self):
        """Should have exactly one per kind (not more) for a given config."""
        dataset = self._dataset()
        from collections import Counter
        kind_counts = Counter(
            r.hard_nonduplicate_kind
            for r in dataset.records
            if r.hard_nonduplicate_kind is not None
        )
        for kind in HardNonduplicateKind:
            self.assertLessEqual(kind_counts[kind], 1, f"more than one hard nonduplicate for {kind.name}")


if __name__ == "__main__":
    unittest.main()
