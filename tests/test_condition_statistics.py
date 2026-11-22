import numpy as np
import pytest

from src.research.condition_statistics import (
    _weighted_sign_flip_pvalue,
    condition_balanced_paired_summary,
)
from scripts.run_tdk_protocol_experiment import (
    PAIR_METRICS,
    PRIMARY_COMPARISON,
    _paired_comparisons,
)


def test_condition_balanced_estimate_does_not_overweight_large_condition() -> None:
    summary = condition_balanced_paired_summary(
        {
            "condition-a": (1.0, 1.0, 1.0, 1.0),
            "condition-b": (-1.0,),
        },
        seed=7,
        bootstrap_samples=500,
        sign_flip_samples=500,
    )

    assert summary.effect_mean == pytest.approx(0.0)
    assert summary.seed_count == 5
    assert summary.condition_count == 2
    assert summary.condition_seed_counts == (4, 1)


def test_hierarchical_interval_is_reproducible() -> None:
    values = {
        "condition-a": (0.2, 0.3, 0.4),
        "condition-b": (-0.1, 0.0, 0.1),
        "condition-c": (0.5, 0.6, 0.7),
    }

    first = condition_balanced_paired_summary(
        values,
        seed=31,
        bootstrap_samples=1_000,
        sign_flip_samples=1_000,
    )
    second = condition_balanced_paired_summary(
        values,
        seed=31,
        bootstrap_samples=1_000,
        sign_flip_samples=1_000,
    )

    assert first == second
    assert first.ci95_low <= first.effect_mean <= first.ci95_high


def test_zero_effect_has_unit_sign_flip_pvalue() -> None:
    summary = condition_balanced_paired_summary(
        {"condition-a": (0.0, 0.0), "condition-b": (0.0,)},
        seed=1,
        bootstrap_samples=100,
        sign_flip_samples=100,
    )

    assert summary.sign_flip_pvalue == 1.0


def test_chunked_sign_flip_matches_single_matrix_sampling() -> None:
    effects = np.linspace(-0.2, 0.4, 25) + 0.001
    samples = 1_000
    expected_rng = np.random.default_rng(91)
    expected_draws = expected_rng.integers(
        0,
        2,
        size=(samples, effects.size),
    )
    expected_signs = expected_draws * 2 - 1
    observed = abs(float(effects.sum()))
    expected_extreme = np.count_nonzero(
        np.abs(expected_signs @ effects) >= observed - 1e-15
    )
    expected = (int(expected_extreme) + 1) / (samples + 1)

    actual = _weighted_sign_flip_pvalue(
        effects,
        np.random.default_rng(91),
        samples,
        max_sign_elements=100,
    )

    assert actual == expected


def test_sign_flip_sampling_is_bounded_for_validation_scale() -> None:
    effects = np.linspace(-0.1, 0.2, 649)

    result = _weighted_sign_flip_pvalue(
        effects,
        np.random.default_rng(17),
        2_000,
        max_sign_elements=1_000,
    )

    assert 0.0 < result <= 1.0


@pytest.mark.parametrize(
    "invalid",
    ({}, {"condition-a": ()}),
)
def test_empty_condition_data_are_rejected(invalid: dict[str, tuple[float, ...]]) -> None:
    with pytest.raises(ValueError, match="condition"):
        condition_balanced_paired_summary(
            invalid,
            seed=1,
            bootstrap_samples=100,
            sign_flip_samples=100,
        )


def test_invalid_resampling_counts_are_rejected() -> None:
    with pytest.raises(ValueError, match="samples"):
        condition_balanced_paired_summary(
            {"condition-a": (1.0,)},
            seed=1,
            bootstrap_samples=0,
            sign_flip_samples=100,
        )


def test_protocol_comparison_reports_condition_balanced_effect() -> None:
    rows: list[dict[str, object]] = []
    effects = {
        "condition-a-seed-01": 1.0,
        "condition-a-seed-02": 1.0,
        "condition-a-seed-03": 1.0,
        "condition-a-seed-04": 1.0,
        "condition-b-seed-01": -1.0,
    }
    for scenario_id, effect in effects.items():
        for representation, value in (
            ("raw_matched", 0.0),
            ("policy_matched", effect),
        ):
            row: dict[str, object] = {
                "scenario_id": scenario_id,
                "method": PRIMARY_COMPARISON[0],
                "representation": representation,
                "operating_point": PRIMARY_COMPARISON[1],
            }
            row.update({metric: value for metric in PAIR_METRICS})
            rows.append(row)

    comparison = _paired_comparisons(rows)[0]

    assert comparison["scenario_count"] == 5
    assert comparison["condition_count"] == 2
    assert comparison["recall_delta_mean"] == pytest.approx(0.0)
    assert comparison["recall_condition_seed_counts"] == "4|1"
    assert comparison["inference_unit"] == "scenario_seed_condition_stratified"
