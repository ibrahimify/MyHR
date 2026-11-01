"""Semantic checks for the synthetic anomaly-review demonstration."""

from dataclasses import fields
import unittest

from src.services.anomaly_detection.demo_pipeline import (
    DemoQueueItem,
    demo_scenario_options,
    run_demo_scenario,
)
from src.core.i18n import TRANSLATIONS


class AnomalyDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.demo_result = run_demo_scenario(
            0, employee_count=120, review_budget=0.10
        )

    def test_demo_uses_fixed_labelled_development_scenarios(self):
        options = demo_scenario_options(employee_count=120)
        self.assertEqual(len(options), 3)
        self.assertEqual(len({option.scenario_id for option in options}), 3)
        self.assertTrue(all(option.employee_count == 120 for option in options))

    def test_demo_labels_exist_in_every_supported_language(self):
        keys = {
            key for key in TRANSLATIONS["en"] if key.startswith("anomaly_demo_")
        }
        self.assertTrue(keys)
        for language in ("hu", "ar"):
            self.assertLessEqual(keys, TRANSLATIONS[language].keys())

    def test_demo_rejects_unknown_scenario(self):
        with self.assertRaisesRegex(ValueError, "unknown demonstration scenario"):
            run_demo_scenario(99, employee_count=30)

    def test_training_validation_and_evaluation_populations_are_separate(self):
        result = self.demo_result
        self.assertGreater(result.train_count, 0)
        self.assertLessEqual(0 < result.model_fit_count, result.train_count)
        self.assertGreater(result.validation_count, 0)
        self.assertGreater(result.test_count, 0)
        self.assertEqual(
            result.train_count + result.validation_count + result.test_count,
            result.scenario.employee_count,
        )
        self.assertTrue(
            all(
                evidence.split == "test"
                for evidence in result.evidence_by_employee_id.values()
            )
        )

    def test_all_ml_methods_use_identical_population_and_review_capacity(self):
        comparisons = self.demo_result.comparisons
        self.assertEqual(
            {item.representation for item in comparisons},
            {
                "raw_matched",
                "policy_matched",
                "wrong_policy_control",
                "shuffled_policy_control",
            },
        )
        self.assertEqual(len({item.evaluation_count for item in comparisons}), 1)
        self.assertEqual(len({item.review_count for item in comparisons}), 1)
        self.assertGreater(comparisons[0].review_count, 0)

    def test_queue_contains_no_generated_truth_or_mechanism_fields(self):
        queue_fields = {field.name for field in fields(DemoQueueItem)}
        self.assertTrue(
            queue_fields.isdisjoint({"label", "truth", "mechanism", "is_anomaly"})
        )
        self.assertTrue(
            all(
                item.employee_id in self.demo_result.evidence_by_employee_id
                for item in self.demo_result.queue
            )
        )

    def test_policy_calculation_arithmetic_is_traceable(self):
        calculations = [
            calculation
            for evidence in self.demo_result.evidence_by_employee_id.values()
            for calculation in evidence.calculations
        ]
        self.assertTrue(calculations)
        for calculation in calculations:
            self.assertEqual(
                calculation.adjusted_service_months,
                calculation.observed_service_months
                + calculation.commendation_credit_months
                - calculation.sanction_delay_months,
            )
            self.assertEqual(
                calculation.service_deficit_months,
                max(
                    calculation.required_service_months
                    - calculation.adjusted_service_months,
                    0,
                ),
            )

    def test_truth_evaluation_is_reported_separately(self):
        summary = self.demo_result.evaluation
        self.assertEqual(
            summary.evaluation_count,
            self.demo_result.comparisons[0].evaluation_count,
        )
        self.assertEqual(
            summary.true_positives + summary.false_negatives,
            summary.positive_count,
        )
        self.assertEqual(
            summary.ml_review_count,
            self.demo_result.comparisons[1].review_count,
        )
