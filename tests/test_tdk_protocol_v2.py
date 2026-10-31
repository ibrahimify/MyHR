import ast
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

from src.services.anomaly_detection.features import (
    extract_policy_aware_features,
    extract_raw_features,
)
from src.services.anomaly_detection.deterministic_checks import (
    validate_invariant_record,
    validate_record_with_policy,
)
from src.services.anomaly_detection.policy_history import PolicyEpoch, assess_promotion_history
from src.services.anomaly_detection.policy_model import (
    PromotionPolicy,
    PromotionRaceInput,
    calculate_promotion_race,
)
from src.services.anomaly_detection.protocol_evaluation import (
    _evaluation_output,
    _rules_first_budget_predictions,
    _select_cascade_threshold,
    _select_threshold,
    _top_budget_predictions,
    evaluate_scenario,
    feature_representations,
)
from src.services.anomaly_detection.scenario_generation import (
    generate_scenario_dataset,
    scenario_matrix,
)
from src.services.anomaly_detection.synthetic_data import (
    AdministrativeEvent,
    AdministrativeEventType,
    AnomalyType,
    DatasetSplit,
    EmployeeIdentity,
    EmploymentTrack,
    WorkforceHistoryRecord,
    serialize_dataset,
)
from scripts.run_tdk_independent_development import _replicate_independent_specs
from scripts.run_tdk_protocol_experiment import (
    MIN_SEEDS_PER_CONDITION,
    PAIR_METRICS,
    PRIMARY_COMPARISON,
    SECONDARY_COMPARISON_METRICS,
    _holm_adjusted_pvalues,
    _paired_comparisons,
    _replicate_scenario_configs,
    _robustness_slices,
    _validate_seed_replication,
)
from src.research.independent_scenarios import independent_scenario_matrix


def _imported_modules(source: str) -> set[str]:
    modules = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            prefix = "." * node.level
            modules.add(f"{prefix}{node.module or ''}")
    return modules


class SharedPolicyContractTests(unittest.TestCase):
    def test_recorded_time_controls_snapshot_feature_visibility(self):
        base = WorkforceHistoryRecord(
            identity=EmployeeIdentity(
                employee_id="EMP-RECORDED",
                full_name="Recorded Time",
                date_of_birth=date(1990, 1, 1),
                national_id="RECORDED-1",
            ),
            employment_track=EmploymentTrack.PROMOTION,
            current_level="L7",
            department="Operations",
            role="Specialist",
            hire_date=date(2020, 1, 1),
            events=(
                AdministrativeEvent(
                    AdministrativeEventType.HIRE,
                    date(2020, 1, 1),
                    "HIRE",
                    recorded_date=date(2020, 1, 2),
                ),
                AdministrativeEvent(
                    AdministrativeEventType.SANCTION,
                    date(2025, 1, 1),
                    "SANCTION",
                    category=1,
                    recorded_date=date(2027, 1, 1),
                ),
            ),
            split=DatasetSplit.TEST,
            anomaly_labels=(AnomalyType.CLEAN,),
            observation_date=date(2026, 12, 31),
        )

        before_correction = extract_raw_features(base).values
        visible_event = replace(
            base.events[1], recorded_date=date(2025, 1, 2)
        )
        after_correction = extract_raw_features(
            replace(base, events=(base.events[0], visible_event))
        ).values

        self.assertEqual(before_correction["sanction_count"], 0.0)
        self.assertEqual(after_correction["sanction_count"], 1.0)

    def test_commendation_on_promotion_date_is_not_reused_in_next_race(self):
        record = WorkforceHistoryRecord(
            identity=EmployeeIdentity(
                employee_id="EMP-BOUNDARY",
                full_name="Boundary Example",
                date_of_birth=date(1990, 1, 1),
                national_id="BOUNDARY-1",
            ),
            employment_track=EmploymentTrack.PROMOTION,
            current_level="L5",
            department="Operations",
            role="Specialist",
            hire_date=date(2018, 1, 1),
            events=(
                AdministrativeEvent(
                    AdministrativeEventType.HIRE, date(2018, 1, 1), "HIRE"
                ),
                AdministrativeEvent(
                    AdministrativeEventType.COMMENDATION,
                    date(2021, 1, 1),
                    "COMM-ON-PROMOTION",
                    category=2,
                ),
                AdministrativeEvent(
                    AdministrativeEventType.PROMOTION,
                    date(2021, 1, 1),
                    "PROM-1",
                    level_before="L7",
                    level_after="L6",
                ),
                AdministrativeEvent(
                    AdministrativeEventType.PROMOTION,
                    date(2024, 1, 1),
                    "PROM-2",
                    level_before="L6",
                    level_after="L5",
                ),
            ),
            split=DatasetSplit.TEST,
            anomaly_labels=(AnomalyType.CLEAN,),
        )

        assessments = assess_promotion_history(record, PromotionPolicy())

        self.assertEqual(assessments[0].commendation_credit_months, 3)
        self.assertEqual(assessments[1].commendation_credit_months, 0)

    def test_invariant_filter_does_not_consume_configurable_service_deficit(self):
        record = WorkforceHistoryRecord(
            identity=EmployeeIdentity(
                employee_id="EMP-POLICY-ONLY",
                full_name="Policy Only",
                date_of_birth=date(1990, 1, 1),
                national_id="POLICY-ONLY-1",
            ),
            employment_track=EmploymentTrack.PROMOTION,
            current_level="L6",
            department="Operations",
            role="Specialist",
            hire_date=date(2020, 1, 1),
            events=(
                AdministrativeEvent(
                    AdministrativeEventType.HIRE, date(2020, 1, 1), "HIRE"
                ),
                AdministrativeEvent(
                    AdministrativeEventType.PROMOTION,
                    date(2022, 1, 1),
                    "PROM",
                    level_before="L7",
                    level_after="L6",
                ),
            ),
            split=DatasetSplit.TEST,
            anomaly_labels=(AnomalyType.FREQUENT_PROMOTIONS,),
        )

        self.assertEqual(validate_invariant_record(record), ())
        self.assertTrue(validate_record_with_policy(record, PromotionPolicy()))

    def test_historical_promotion_uses_effective_policy_epoch(self):
        record = WorkforceHistoryRecord(
            identity=EmployeeIdentity(
                employee_id="EMP-HISTORICAL",
                full_name="Historical Policy",
                date_of_birth=date(1990, 1, 1),
                national_id="HISTORICAL-1",
            ),
            employment_track=EmploymentTrack.PROMOTION,
            current_level="L6",
            department="Operations",
            role="Specialist",
            hire_date=date(2020, 1, 1),
            events=(
                AdministrativeEvent(
                    AdministrativeEventType.HIRE,
                    date(2020, 1, 1),
                    "HIRE",
                    recorded_date=date(2020, 1, 2),
                    policy_id="legacy",
                ),
                AdministrativeEvent(
                    AdministrativeEventType.PROMOTION,
                    date(2022, 7, 1),
                    "PROM",
                    level_before="L7",
                    level_after="L6",
                    recorded_date=date(2022, 7, 2),
                    policy_id="legacy",
                ),
            ),
            split=DatasetSplit.TEST,
            anomaly_labels=(AnomalyType.CLEAN,),
        )
        legacy = PromotionPolicy(service_months_by_level={"L7": 30})
        current = PromotionPolicy(service_months_by_level={"L7": 36})
        epochs = (
            PolicyEpoch(
                policy_id="legacy",
                version="1.0",
                valid_from=date(2018, 1, 1),
                valid_to=date(2022, 12, 31),
                recorded_at=date(2017, 12, 1),
                jurisdiction="organization-wide",
                policy=legacy,
            ),
            PolicyEpoch(
                policy_id="current",
                version="2.0",
                valid_from=date(2023, 1, 1),
                valid_to=None,
                recorded_at=date(2022, 10, 1),
                jurisdiction="organization-wide",
                policy=current,
            ),
        )

        self.assertEqual(
            assess_promotion_history(record, current)[0].service_deficit_months,
            6,
        )
        self.assertEqual(
            assess_promotion_history(record, current, epochs)[0].service_deficit_months,
            0,
        )

    def test_application_database_does_not_import_research_package(self):
        source = Path("src/database/connection.py").read_text(encoding="utf-8")
        imported_modules = _imported_modules(source)

        self.assertFalse(any(
            module.startswith("src.services.anomaly_detection")
            for module in imported_modules
        ))

    def test_race_contract_applies_commendations_and_active_sanctions(self):
        outcome = calculate_promotion_race(PromotionRaceInput(
            has_next_level=True,
            base_months=36,
            months_elapsed=30,
            commendation_credit_months=3,
            active_sanction_delay_months=2,
        ))

        self.assertEqual(outcome.adjusted_service_months, 31)
        self.assertEqual(outcome.months_remaining, 5)
        self.assertFalse(outcome.eligible)
        self.assertEqual(outcome.progress_pct, 86)

    def test_other_track_has_no_promotion_result(self):
        outcome = calculate_promotion_race(PromotionRaceInput(
            has_next_level=False,
            base_months=None,
            months_elapsed=48,
            commendation_credit_months=12,
            active_sanction_delay_months=6,
        ))

        self.assertFalse(outcome.has_next_level)
        self.assertIsNone(outcome.months_remaining)
        self.assertFalse(outcome.eligible)
        self.assertEqual(outcome.progress_pct, 0)

    def test_policy_history_detects_invalid_earlier_promotion(self):
        record = WorkforceHistoryRecord(
            identity=EmployeeIdentity(
                employee_id="HISTORY-1",
                full_name="History Test",
                date_of_birth=date(1990, 1, 1),
            ),
            split=DatasetSplit.TEST,
            employment_track=EmploymentTrack.PROMOTION,
            current_level="L5",
            department="Research",
            role="Engineer",
            hire_date=date(2020, 1, 1),
            events=(
                AdministrativeEvent(
                    AdministrativeEventType.PROMOTION,
                    date(2021, 9, 1),
                    "PROM-INVALID",
                    level_before="L7",
                    level_after="L6",
                ),
                AdministrativeEvent(
                    AdministrativeEventType.PROMOTION,
                    date(2024, 9, 1),
                    "PROM-VALID",
                    level_before="L6",
                    level_after="L5",
                ),
            ),
            anomaly_labels=(AnomalyType.FREQUENT_PROMOTIONS,),
        )

        findings = validate_record_with_policy(record, PromotionPolicy())
        policy_findings = [
            finding for finding in findings
            if finding.code == "promotion_policy_service_deficit"
        ]
        features = extract_policy_aware_features(record, PromotionPolicy()).values

        self.assertEqual(len(policy_findings), 1)
        self.assertEqual(policy_findings[0].event_source_id, "PROM-INVALID")
        self.assertEqual(features["policy_service_deficit_months"], 16.0)
        self.assertEqual(features["policy_unexplained_short_promotion"], 1.0)


class ScenarioGenerationTests(unittest.TestCase):
    def test_generator_does_not_import_detection_or_feature_modules(self):
        source = Path(
            "src/services/anomaly_detection/scenario_generation.py"
        ).read_text(encoding="utf-8")
        forbidden_modules = {
            ".deterministic_checks",
            ".features",
            ".isolation_forest",
            ".protocol_evaluation",
            ".statistical_baselines",
        }

        self.assertTrue(forbidden_modules.isdisjoint(_imported_modules(source)))

    def test_development_and_validation_seed_ranges_are_disjoint(self):
        development = scenario_matrix("development", count=30, employee_count=120)
        validation = scenario_matrix("validation", count=30, employee_count=120)

        self.assertFalse({item.dataset_seed for item in development} & {item.dataset_seed for item in validation})
        self.assertFalse({item.split_seed for item in development} & {item.split_seed for item in validation})
        self.assertFalse({item.model_seed for item in development} & {item.model_seed for item in validation})

    def test_holdout_scenario_generation_is_locked(self):
        with self.assertRaisesRegex(ValueError, "holdout"):
            scenario_matrix("holdout", count=1, employee_count=120)

    def test_matrix_covers_all_predeclared_scenario_dimensions(self):
        configs = scenario_matrix("development", count=30, employee_count=120)

        self.assertEqual({config.policy_profile for config in configs}, {"standard", "accelerated", "conservative"})
        self.assertEqual(
            {config.population_profile for config in configs},
            {"balanced", "experienced", "mixed_workforce"},
        )
        self.assertEqual(
            {config.anomaly_mechanism for config in configs},
            {"mixed_calendar", "mixed_process", "mixed_density"},
        )
        self.assertEqual(
            {config.rare_pattern for config in configs},
            {"credit_mix", "credit_with_delay", "boundary_case"},
        )
        for policy in {config.policy_profile for config in configs}:
            policy_configs = [config for config in configs if config.policy_profile == policy]
            self.assertEqual(
                {config.anomaly_mechanism for config in policy_configs},
                {"mixed_calendar", "mixed_process", "mixed_density"},
            )
            self.assertEqual(
                {config.rare_pattern for config in policy_configs},
                {"credit_mix", "credit_with_delay", "boundary_case"},
            )
        factorial = {
            (config.policy_profile, config.population_profile, config.anomaly_mechanism)
            for config in configs[:27]
        }
        self.assertEqual(len(factorial), 27)

    def test_generation_is_reproducible(self):
        config = scenario_matrix("development", count=1, employee_count=120)[0]

        first = generate_scenario_dataset(config)
        second = generate_scenario_dataset(config)

        self.assertEqual(serialize_dataset(first.dataset), serialize_dataset(second.dataset))

    def test_clean_and_rare_histories_satisfy_assigned_policy(self):
        for config in scenario_matrix("development", count=6, employee_count=120):
            scenario = generate_scenario_dataset(config)
            for record in scenario.dataset.records:
                if record.has_progression_anomaly or record.employment_track is EmploymentTrack.OTHER:
                    continue
                features = extract_policy_aware_features(record, scenario.policy).values
                self.assertEqual(
                    features["policy_service_deficit_months"],
                    0.0,
                    msg=f"{config.scenario_id}:{record.identity.employee_id}",
                )

    def test_rare_cases_exist_in_each_split_and_only_on_promotion_track(self):
        scenario = generate_scenario_dataset(
            scenario_matrix("validation", count=1, employee_count=300)[0]
        )
        rare = [
            record for record in scenario.dataset.records
            if AnomalyType.POLICY_LEGITIMATE_RARE_CASE in record.anomaly_labels
        ]

        self.assertEqual({record.split for record in rare}, set(DatasetSplit))
        self.assertTrue(all(record.employment_track is EmploymentTrack.PROMOTION for record in rare))

    def test_policy_rules_separate_unexplained_and_legitimate_short_promotions(self):
        scenario = generate_scenario_dataset(
            scenario_matrix("validation", count=1, employee_count=300)[0]
        )
        frequent = next(
            record for record in scenario.dataset.records
            if AnomalyType.FREQUENT_PROMOTIONS in record.anomaly_labels
        )
        rare = next(
            record for record in scenario.dataset.records
            if AnomalyType.POLICY_LEGITIMATE_RARE_CASE in record.anomaly_labels
        )

        frequent_codes = {finding.code for finding in validate_record_with_policy(frequent, scenario.policy)}
        rare_codes = {finding.code for finding in validate_record_with_policy(rare, scenario.policy)}

        self.assertIn("promotion_policy_service_deficit", frequent_codes)
        self.assertNotIn("promotion_policy_service_deficit", rare_codes)


class ValidationProtocolTests(unittest.TestCase):
    def test_protocol_conditions_have_thirty_independent_seed_replicates(self):
        condition = scenario_matrix(
            "development",
            count=1,
            employee_count=120,
        )[0]

        configs = _replicate_scenario_configs(
            (condition,),
            MIN_SEEDS_PER_CONDITION,
        )

        self.assertEqual(len(configs), 30)
        self.assertEqual(len({item.scenario_id for item in configs}), 30)
        self.assertEqual(len({item.dataset_seed for item in configs}), 30)
        self.assertEqual(len({item.split_seed for item in configs}), 30)
        self.assertEqual(len({item.model_seed for item in configs}), 30)
        self.assertEqual({item.policy_profile for item in configs}, {condition.policy_profile})
        self.assertEqual(
            {item.population_profile for item in configs},
            {condition.population_profile},
        )
        self.assertEqual(
            {item.anomaly_mechanism for item in configs},
            {condition.anomaly_mechanism},
        )

    def test_independent_conditions_have_thirty_seed_replicates(self):
        condition = independent_scenario_matrix(employee_count=120)[0]

        specs = _replicate_independent_specs(
            (condition,),
            MIN_SEEDS_PER_CONDITION,
        )

        self.assertEqual(len(specs), 30)
        self.assertEqual(len({item.scenario_id for item in specs}), 30)
        self.assertEqual(len({item.seed for item in specs}), 30)
        self.assertEqual(len({item.split_seed for item in specs}), 30)
        self.assertEqual(len({item.model_seed for item in specs}), 30)
        self.assertEqual({item.population for item in specs}, {condition.population})
        self.assertEqual({item.mechanism for item in specs}, {condition.mechanism})
        self.assertEqual({item.rare_pattern for item in specs}, {condition.rare_pattern})

    def test_fewer_than_thirty_seeds_requires_written_justification(self):
        with self.assertRaisesRegex(ValueError, "written justification"):
            _validate_seed_replication(2, "")

        _validate_seed_replication(2, "Tiny regression fixture only.")
        _validate_seed_replication(30, "")

    def test_fixed_review_budget_has_exact_alert_count(self):
        predictions = _top_budget_predictions(tuple(float(value) for value in range(20)), 0.10)

        self.assertEqual(sum(predictions), 2)
        self.assertTrue(predictions[-1])
        self.assertTrue(predictions[-2])

    def test_fixed_budget_tie_breaking_is_order_independent_with_stable_ids(self):
        first_ids = ("E1", "E2", "E3", "E4")
        first = _top_budget_predictions((1.0, 1.0, 1.0, 1.0), 0.50, first_ids)
        selected_first = {item for item, chosen in zip(first_ids, first) if chosen}
        second_ids = tuple(reversed(first_ids))
        second = _top_budget_predictions((1.0, 1.0, 1.0, 1.0), 0.50, second_ids)
        selected_second = {item for item, chosen in zip(second_ids, second) if chosen}

        self.assertEqual(selected_first, selected_second)

    def test_holm_adjustment_controls_one_declared_family(self):
        adjusted = _holm_adjusted_pvalues([0.01, 0.03, 0.04])

        self.assertEqual(adjusted, [0.03, 0.06, 0.06])

    def test_primary_and_secondary_inference_families_are_explicit(self):
        rows = []
        for scenario_id, zero_positive in (("s1", False), ("s2", True)):
            for representation, offset in (
                ("raw_matched", 0.0),
                ("policy_matched", 0.1),
            ):
                row = {
                    "scenario_id": scenario_id,
                    "method": PRIMARY_COMPARISON[0],
                    "representation": representation,
                    "operating_point": PRIMARY_COMPARISON[1],
                }
                row.update({metric: 0.4 + offset for metric in PAIR_METRICS})
                if zero_positive:
                    row["recall"] = None
                    row["average_precision"] = None
                rows.append(row)

        comparison = _paired_comparisons(rows)[0]

        self.assertEqual(comparison["scenario_count"], 2)
        self.assertEqual(comparison["comparison_role"], "primary_raw_vs_policy")
        self.assertEqual(comparison["primary_endpoint"], "recall")
        self.assertEqual(comparison["recall_scenario_count"], 1)
        self.assertEqual(comparison["average_precision_scenario_count"], 1)
        self.assertEqual(
            comparison["secondary_family_declared_size"],
            len(SECONDARY_COMPARISON_METRICS),
        )
        self.assertEqual(
            comparison["secondary_family_tested_size"],
            len(SECONDARY_COMPARISON_METRICS),
        )
        self.assertEqual(
            comparison["primary_recall_sign_flip_p"],
            comparison["recall_delta_sign_flip_p"],
        )
        for metric in SECONDARY_COMPARISON_METRICS:
            self.assertIn(f"{metric}_delta_holm_secondary_p", comparison)

    def test_zero_positive_scenarios_remain_in_robustness_output(self):
        rows = []
        for scenario_id, recall, average_precision in (
            ("s1", None, None),
            ("s2", 0.5, 0.6),
        ):
            row = {
                "scenario_id": scenario_id,
                "method": PRIMARY_COMPARISON[0],
                "representation": "raw_matched",
                "operating_point": PRIMARY_COMPARISON[1],
                "policy_profile": "standard",
                "population_profile": "balanced",
                "anomaly_mechanism": "mixed_calendar",
                "rare_pattern": "credit_mix",
                "configured_anomaly_rate": 0.1,
                "configured_rare_rate": 0.05,
                "recall": recall,
                "average_precision": average_precision,
            }
            for metric in (
                "precision",
                "f1",
                "false_positive_rate",
                "alert_rate",
                "rare_legitimate_flagged_rate",
                "ordinary_clean_flagged_rate",
                "anomalies_found_per_100_reviews",
                "rare_legitimate_reviews_per_1000_employees",
                "missed_anomalies_per_1000_employees",
            ):
                row[metric] = 0.25
            rows.append(row)

        slices = _robustness_slices(rows)
        policy_slice = next(
            item for item in slices
            if item["slice_dimension"] == "policy_profile"
        )

        self.assertEqual(policy_slice["scenario_count"], 2)
        self.assertEqual(policy_slice["recall_scenario_count"], 1)
        self.assertEqual(policy_slice["average_precision_scenario_count"], 1)

    def test_validation_f1_threshold_is_selected_only_from_supplied_validation_data(self):
        selection = _select_threshold(
            [False, False, True, True],
            (0.1, 0.2, 0.8, 0.9),
            "validation_f1",
        )

        self.assertEqual(selection.validation_metrics.f1, 1.0)
        self.assertEqual(selection.validation_alert_count, 2)
        self.assertGreater(selection.threshold, 0.2)

    def test_target_fpr_selection_respects_validation_constraint(self):
        selection = _select_threshold(
            [False, False, False, True, True],
            (0.1, 0.2, 0.3, 0.7, 0.9),
            "validation_target_fpr",
            target_fpr=0.0,
        )

        self.assertEqual(selection.validation_metrics.false_positive_rate, 0.0)
        self.assertEqual(selection.validation_metrics.recall, 1.0)

    def test_rules_first_budget_never_drops_rule_findings(self):
        predictions = _rules_first_budget_predictions(
            (1.0, 1.0, 1.0, 0.0, 0.0),
            (0.1, 0.2, 0.3, 0.9, 0.8),
            0.20,
        )

        self.assertEqual(predictions, [True, True, True, False, False])

    def test_rules_first_budget_uses_ml_only_for_remaining_capacity(self):
        predictions = _rules_first_budget_predictions(
            (1.0, 0.0, 0.0, 0.0, 0.0),
            (0.1, 0.2, 0.8, 0.9, 0.7),
            0.40,
        )

        self.assertEqual(predictions, [True, False, False, True, False])

    def test_cascade_threshold_cannot_remove_rule_findings(self):
        selection = _select_cascade_threshold(
            [True, False, True, False],
            (1.0, 0.0, 1.0, 0.0),
            (0.1, 0.9, 0.2, 0.8),
            "validation_f1",
        )

        self.assertEqual(selection.validation_metrics.recall, 1.0)
        self.assertGreaterEqual(selection.validation_alert_count, 2)

    def test_cascade_reports_infeasible_target_fpr_without_dropping_rules(self):
        selection = _select_cascade_threshold(
            [False, False, True, False],
            (1.0, 0.0, 1.0, 0.0),
            (0.1, 0.9, 0.2, 0.8),
            "validation_target_fpr",
            target_fpr=0.0,
        )

        self.assertFalse(selection.constraint_satisfied)
        self.assertEqual(selection.validation_alert_count, 2)
        self.assertEqual(selection.validation_metrics.false_positive_rate, 1 / 3)

    def test_evaluation_reports_fair_budget_denominators_and_controls(self):
        scenario = generate_scenario_dataset(
            scenario_matrix("development", count=1, employee_count=120)[0]
        )
        result = evaluate_scenario(scenario)
        fixed_iforest = [
            row for row in result.metric_rows
            if row["method"] == "isolation_forest"
            and row["operating_point"] == "fixed_review_budget"
        ]
        representations = {row["representation"] for row in fixed_iforest}
        alert_counts = {int(row["alert_count"]) for row in fixed_iforest}
        evaluation_counts = {int(row["evaluation_count"]) for row in fixed_iforest}

        self.assertEqual(representations, {item.name for item in feature_representations()})
        self.assertEqual(len(alert_counts), 1)
        self.assertEqual(len(evaluation_counts), 1)
        for row in result.metric_rows:
            self.assertEqual(
                int(row["positive_count"]) + int(row["negative_count"]),
                int(row["evaluation_count"]),
            )
            self.assertEqual(
                int(row["true_positives"])
                + int(row["false_positives"])
                + int(row["true_negatives"])
                + int(row["false_negatives"]),
                int(row["evaluation_count"]),
            )
        self.assertIn("wrong_policy_control", representations)
        self.assertIn("shuffled_policy_control", representations)
        self.assertTrue(any(row["method"] == "deterministic_rules" for row in result.metric_rows))
        self.assertTrue(any(
            row["method"] == "deterministic_invariant_rules"
            for row in result.metric_rows
        ))
        self.assertTrue(any(row["method"] == "deterministic_policy_rules" for row in result.metric_rows))
        cascade_rows = [
            row for row in result.metric_rows
            if row["method"] == "policy_rules_plus_isolation_forest"
        ]
        self.assertTrue(cascade_rows)
        self.assertTrue(any(
            row["operating_point"] == "rules_first_budget_floor"
            for row in cascade_rows
        ))
        rule_alerts = next(
            int(row["alert_count"])
            for row in result.metric_rows
            if row["method"] == "deterministic_policy_rules"
        )
        self.assertTrue(all(
            int(row["alert_count"]) >= rule_alerts
            for row in cascade_rows
        ))

        primary_predictions = [
            row for row in result.prediction_rows
            if row["method"] == "rule_negative_isolation_forest"
            and row["operating_point"] == "fixed_review_budget"
            and row["representation"] in {"raw_matched", "policy_matched"}
        ]
        ids_by_representation = {
            representation: {
                row["employee_id"] for row in primary_predictions
                if row["representation"] == representation
            }
            for representation in ("raw_matched", "policy_matched")
        }
        self.assertEqual(
            ids_by_representation["raw_matched"],
            ids_by_representation["policy_matched"],
        )

    def test_zero_positive_metrics_are_explicitly_undefined(self):
        scenario = generate_scenario_dataset(
            scenario_matrix("development", count=1, employee_count=120)[0]
        )
        records = tuple(
            record for record in scenario.dataset.records
            if record.split is DatasetSplit.TEST
        )[:3]

        row, _ = _evaluation_output(
            scenario,
            records,
            [False, False, False],
            (0.3, 0.2, 0.1),
            [True, False, False],
            method="contract_probe",
            representation="raw_matched",
            operating_point="fixed_review_budget",
            threshold=None,
            validation_selection=None,
            runtime_ms=0.0,
        )

        self.assertFalse(row["recall_defined"])
        self.assertFalse(row["average_precision_defined"])
        self.assertIsNone(row["recall"])
        self.assertIsNone(row["average_precision"])


if __name__ == "__main__":
    unittest.main()
