import unittest
from datetime import datetime, timedelta

from src.services.anomaly_detection import ExperimentConfig, PromotionPolicy, confusion_counts, split_indices
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


if __name__ == "__main__":
    unittest.main()
