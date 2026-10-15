import ast
import unittest
from datetime import date
from pathlib import Path

from src.services.anomaly_detection.features import extract_policy_aware_features
from src.services.anomaly_detection.deterministic_checks import validate_record_with_policy
from src.services.anomaly_detection.policy_model import (
    PromotionPolicy,
    PromotionRaceInput,
    calculate_promotion_race,
)
from src.services.anomaly_detection.protocol_evaluation import (
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
from scripts.run_tdk_protocol_experiment import _holm_adjusted_pvalues


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


if __name__ == "__main__":
    unittest.main()
