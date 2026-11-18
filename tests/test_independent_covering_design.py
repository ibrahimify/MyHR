from dataclasses import replace
from collections import Counter
from itertools import combinations, product

import pytest

from src.research.independent_scenarios import (
    anomaly_mechanisms,
    compatible_rare_patterns_by_population,
    generate_independent_world,
    independent_covering_scenario_matrix,
    policy_variants,
    population_families,
    rare_legitimate_patterns,
)


def _factor_values(spec) -> tuple[object, ...]:
    return (
        spec.policy_variant,
        spec.population,
        spec.mechanism,
        spec.rare_pattern,
        spec.error_rate,
        spec.rare_rate,
    )


def test_covering_matrix_has_no_duplicate_condition_signatures() -> None:
    specs = independent_covering_scenario_matrix("independent_development")
    signatures = {_factor_values(spec) for spec in specs}

    assert len(specs) == len(signatures)
    assert all(spec.run_purpose == "independent_development" for spec in specs)


def test_covering_matrix_has_balanced_factor_margins() -> None:
    specs = independent_covering_scenario_matrix("independent_development")

    assert len(specs) == 36
    for factor_name in (
        "policy_variant",
        "population",
        "mechanism",
        "rare_pattern",
        "error_rate",
        "rare_rate",
    ):
        counts = Counter(getattr(spec, factor_name) for spec in specs)
        assert max(counts.values()) - min(counts.values()) <= 1


def test_covering_matrix_covers_every_valid_factor_pair() -> None:
    specs = independent_covering_scenario_matrix("independent_development")
    actual = {
        (left_index, left, right_index, right)
        for spec in specs
        for left_index, right_index in combinations(range(6), 2)
        for left, right in [(_factor_values(spec)[left_index], _factor_values(spec)[right_index])]
    }
    candidates = []
    for policy, population, mechanism, rare, error_rate, rare_rate in product(
        policy_variants(),
        population_families(),
        anomaly_mechanisms(),
        rare_legitimate_patterns(),
        (0.08, 0.16),
        (0.04, 0.10),
    ):
        if rare in compatible_rare_patterns_by_population()[population]:
            candidates.append((policy, population, mechanism, rare, error_rate, rare_rate))
    expected = {
        (left_index, values[left_index], right_index, values[right_index])
        for values in candidates
        for left_index, right_index in combinations(range(6), 2)
    }

    assert actual == expected


def test_development_and_validation_designs_use_disjoint_seeds() -> None:
    development = independent_covering_scenario_matrix("independent_development")
    validation = independent_covering_scenario_matrix("independent_validation")

    assert {_factor_values(spec) for spec in development} == {
        _factor_values(spec) for spec in validation
    }
    assert {spec.seed for spec in development}.isdisjoint({spec.seed for spec in validation})
    assert {spec.split_seed for spec in development}.isdisjoint({
        spec.split_seed for spec in validation
    })
    assert {spec.model_seed for spec in development}.isdisjoint({
        spec.model_seed for spec in validation
    })


def test_holdout_design_remains_unavailable() -> None:
    with pytest.raises(ValueError, match="holdout"):
        independent_covering_scenario_matrix("holdout")


def test_policy_variants_change_observable_policy_cards() -> None:
    base = independent_covering_scenario_matrix(
        "independent_development",
        employee_count=120,
    )[0]
    requirements = {}
    for offset, variant in enumerate(policy_variants()):
        world = generate_independent_world(replace(
            base,
            scenario_id=f"policy-{variant}",
            policy_variant=variant,
            seed=91_000 + offset * 100,
            split_seed=91_003 + offset * 100,
            model_seed=91_007 + offset * 100,
        ))
        current = max(world.policies, key=lambda card: card.effective_from)
        requirements[variant] = current.service_months_by_level["L7"]

    assert requirements == {
        "accelerated": 30,
        "standard": 36,
        "conservative": 42,
    }
