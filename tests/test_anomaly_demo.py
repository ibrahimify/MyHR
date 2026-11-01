"""Semantic checks for the synthetic anomaly-review demonstration."""

from dataclasses import fields

import pytest

from src.services.anomaly_detection.demo_pipeline import (
    DemoQueueItem,
    demo_scenario_options,
    run_demo_scenario,
)
from src.core.i18n import TRANSLATIONS


@pytest.fixture(scope="module")
def demo_result():
    return run_demo_scenario(0, employee_count=120, review_budget=0.10)


def test_demo_uses_fixed_labelled_development_scenarios():
    options = demo_scenario_options(employee_count=120)
    assert len(options) == 3
    assert len({option.scenario_id for option in options}) == 3
    assert all(option.employee_count == 120 for option in options)


def test_demo_labels_exist_in_every_supported_language():
    keys = {
        key for key in TRANSLATIONS["en"]
        if key.startswith("anomaly_demo_")
    }
    assert keys
    for language in ("hu", "ar"):
        assert keys <= TRANSLATIONS[language].keys()


def test_demo_rejects_unknown_scenario():
    with pytest.raises(ValueError, match="unknown demonstration scenario"):
        run_demo_scenario(99, employee_count=30)


def test_training_validation_and_evaluation_populations_are_separate(demo_result):
    assert demo_result.train_count > 0
    assert 0 < demo_result.model_fit_count <= demo_result.train_count
    assert demo_result.validation_count > 0
    assert demo_result.test_count > 0
    assert (
        demo_result.train_count
        + demo_result.validation_count
        + demo_result.test_count
        == demo_result.scenario.employee_count
    )
    assert all(
        evidence.split == "test"
        for evidence in demo_result.evidence_by_employee_id.values()
    )


def test_all_ml_methods_use_identical_population_and_review_capacity(demo_result):
    comparisons = demo_result.comparisons
    assert {item.representation for item in comparisons} == {
        "raw_matched",
        "policy_matched",
        "wrong_policy_control",
        "shuffled_policy_control",
    }
    assert len({item.evaluation_count for item in comparisons}) == 1
    assert len({item.review_count for item in comparisons}) == 1
    assert comparisons[0].review_count > 0


def test_queue_contains_no_generated_truth_or_mechanism_fields(demo_result):
    queue_fields = {field.name for field in fields(DemoQueueItem)}
    assert queue_fields.isdisjoint({"label", "truth", "mechanism", "is_anomaly"})
    assert all(
        item.employee_id in demo_result.evidence_by_employee_id
        for item in demo_result.queue
    )


def test_policy_calculation_arithmetic_is_traceable(demo_result):
    calculations = [
        calculation
        for evidence in demo_result.evidence_by_employee_id.values()
        for calculation in evidence.calculations
    ]
    assert calculations
    for calculation in calculations:
        assert calculation.adjusted_service_months == (
            calculation.observed_service_months
            + calculation.commendation_credit_months
            - calculation.sanction_delay_months
        )
        assert calculation.service_deficit_months == max(
            calculation.required_service_months
            - calculation.adjusted_service_months,
            0,
        )


def test_truth_evaluation_is_reported_separately(demo_result):
    summary = demo_result.evaluation
    assert summary.evaluation_count == demo_result.comparisons[0].evaluation_count
    assert summary.true_positives + summary.false_negatives == summary.positive_count
    assert summary.ml_review_count == demo_result.comparisons[1].review_count
