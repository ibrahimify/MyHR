from dataclasses import replace
from collections import Counter
import csv
from itertools import combinations, product
from types import SimpleNamespace

import pytest

from src.research import holdout_gate
from scripts.run_tdk_independent_development import _select_independent_conditions
from scripts.run_tdk_independent_development import _begin_holdout_if_authorized
from scripts.run_tdk_independent_development import _replicate_independent_specs
from scripts.run_tdk_independent_development import _protocol_status
from scripts.run_tdk_independent_development import _normalized_text_sha256
from scripts.combine_tdk_independent_shards import (
    _concatenate_csv_files,
    _validate_shard_set,
)
from src.research.independent_scenarios import (
    anomaly_mechanisms,
    compatible_rare_patterns_by_population,
    generate_independent_world,
    independent_condition_matrix_sha256,
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


def _test_holdout_attempt(tmp_path) -> holdout_gate.HoldoutAttempt:
    return holdout_gate.HoldoutAttempt(
        attempt_id="test-attempt",
        authorization_sha256="a" * 64,
        frozen_git_commit="b" * 40,
        matrix_sha256="c" * 64,
        ledger_path=tmp_path / "ledger.json",
        _capability_nonce=holdout_gate._CAPABILITY_NONCE,
    )


def test_frozen_text_digest_is_independent_of_checkout_line_endings(tmp_path) -> None:
    lf_path = tmp_path / "lf.txt"
    crlf_path = tmp_path / "crlf.txt"
    lf_path.write_bytes(b"first\nsecond\n")
    crlf_path.write_bytes(b"first\r\nsecond\r\n")

    assert _normalized_text_sha256(lf_path) == _normalized_text_sha256(crlf_path)


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


def test_authorized_holdout_design_is_factor_matched_and_seed_disjoint(tmp_path) -> None:
    development = independent_covering_scenario_matrix("independent_development")
    validation = independent_covering_scenario_matrix("independent_validation")
    holdout = independent_covering_scenario_matrix(
        "independent_holdout",
        holdout_attempt=_test_holdout_attempt(tmp_path),
    )

    assert {_factor_values(spec) for spec in holdout} == {
        _factor_values(spec) for spec in development
    }
    for existing in (development, validation):
        assert {spec.seed for spec in holdout}.isdisjoint({spec.seed for spec in existing})
        assert {spec.split_seed for spec in holdout}.isdisjoint({
            spec.split_seed for spec in existing
        })
        assert {spec.model_seed for spec in holdout}.isdisjoint({
            spec.model_seed for spec in existing
        })
    assert all(spec.run_purpose == "independent_holdout" for spec in holdout)
    assert min(spec.seed for spec in holdout) == 421_001
    assert independent_condition_matrix_sha256(holdout) == (
        "ca6bdc2a3977485e8e7d48deb4d64666b15a1f572663882c3d58bdb026ada139"
    )
    with pytest.raises(ValueError, match="capability"):
        generate_independent_world(holdout[0])


def test_protocol_status_names_the_actual_partition() -> None:
    assert _protocol_status("independent_development") == (
        "draft_independent_development_holdout_locked"
    )
    assert _protocol_status("independent_validation") == (
        "draft_independent_validation_holdout_locked"
    )
    assert _protocol_status("independent_holdout") == "frozen_independent_holdout"
    with pytest.raises(ValueError, match="unsupported run purpose"):
        _protocol_status("unknown")


def test_seed_shards_equal_monolithic_replication() -> None:
    conditions = independent_covering_scenario_matrix(
        "independent_development",
        employee_count=120,
    )[:2]
    monolithic = _replicate_independent_specs(conditions, 3)
    sharded = tuple(
        spec
        for replicate in (1, 2, 3)
        for spec in _replicate_independent_specs(
            conditions,
            1,
            start_replicate=replicate,
        )
    )

    assert {spec.scenario_id: spec for spec in monolithic} == {
        spec.scenario_id: spec for spec in sharded
    }


def test_shard_combiner_requires_complete_nonoverlapping_replicates() -> None:
    base = {
        "protocol_version": "test",
        "protocol_status": "draft_holdout_locked",
        "analysis_plan_version": "test",
        "run_purpose": "development",
        "generator_run_purpose": "independent_development",
        "design": "covering",
        "artifact_schema_version": 7,
        "condition_count": 2,
        "employee_count_per_scenario": 120,
        "review_budget": 0.1,
        "target_validation_fpr": 0.05,
        "model_comparison_included": True,
        "holdout_accessed": False,
        "provenance": {"git_commit": "abc123"},
    }
    metadata = [dict(base), dict(base), dict(base)]
    shards = []
    for replicate in (1, 2, 3):
        shards.append([{
            "scenario_id": f"{condition}-seed-{replicate:02d}",
            "condition_id": condition,
            "seed_replicate": str(replicate),
        } for condition in ("c1", "c2")])

    _, combined = _validate_shard_set(
        metadata,
        shards,
        expected_seeds_per_condition=3,
    )
    assert len(combined) == 6

    with pytest.raises(ValueError, match="incomplete"):
        _validate_shard_set(
            metadata[:2],
            shards[:2],
            expected_seeds_per_condition=3,
        )
    with pytest.raises(ValueError, match="overlapping"):
        _validate_shard_set(
            metadata,
            [shards[0], shards[0], shards[2]],
            expected_seeds_per_condition=3,
        )


def test_shard_combiner_rejects_mixed_source_revisions() -> None:
    base = {
        "protocol_version": "test",
        "protocol_status": "draft_holdout_locked",
        "analysis_plan_version": "test",
        "run_purpose": "development",
        "generator_run_purpose": "independent_development",
        "design": "covering",
        "artifact_schema_version": 7,
        "condition_count": 1,
        "employee_count_per_scenario": 120,
        "review_budget": 0.1,
        "target_validation_fpr": 0.05,
        "model_comparison_included": True,
        "holdout_accessed": False,
        "provenance": {"git_commit": "abc123"},
    }
    changed = {**base, "provenance": {"git_commit": "different"}}
    configs = [[{
        "scenario_id": "c1-seed-01",
        "condition_id": "c1",
        "seed_replicate": "1",
    }], [{
        "scenario_id": "c1-seed-02",
        "condition_id": "c1",
        "seed_replicate": "2",
    }]]

    with pytest.raises(ValueError, match="different revisions"):
        _validate_shard_set(
            [base, changed],
            configs,
            expected_seeds_per_condition=2,
        )


def test_holdout_design_remains_unavailable() -> None:
    with pytest.raises(ValueError, match="capability"):
        independent_covering_scenario_matrix("independent_holdout")


def test_runner_requires_covering_design_for_validation() -> None:
    with pytest.raises(ValueError, match="no validation design"):
        _select_independent_conditions(
            "independent_validation",
            "legacy",
            120,
        )

    validation = _select_independent_conditions(
        "independent_validation",
        "covering",
        120,
    )
    assert len(validation) == 36
    assert all(spec.run_purpose == "independent_validation" for spec in validation)


def test_holdout_runner_requires_external_authorization_and_ledger(tmp_path) -> None:
    conditions = independent_covering_scenario_matrix(
        "independent_holdout",
        employee_count=120,
        holdout_attempt=_test_holdout_attempt(tmp_path),
    )
    args = SimpleNamespace(
        run_purpose="independent_holdout",
        design="covering",
        employee_count=120,
        seeds_per_condition=30,
        seed_replicate_start=1,
        review_budget=0.10,
        target_validation_fpr=0.05,
        include_model_comparison=True,
        authorization_file=None,
    )

    with pytest.raises(ValueError, match="authorization file"):
        _begin_holdout_if_authorized(args)

    args.authorization_file = tmp_path / "authorization.json"
    with pytest.raises(ValueError, match="not frozen"):
        _begin_holdout_if_authorized(args)

    with pytest.raises(ValueError, match="capability"):
        _select_independent_conditions(
            "independent_holdout",
            "covering",
            120,
        )


def test_combined_record_csvs_are_streamed_with_one_header(tmp_path) -> None:
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    output = tmp_path / "combined.csv"
    first.write_text("id,value\n1,alpha\n2,beta\n", encoding="utf-8")
    second.write_text("id,value\n3,gamma\n", encoding="utf-8")

    _concatenate_csv_files(output, (first, second))

    with output.open(newline="", encoding="utf-8") as handle:
        assert list(csv.DictReader(handle)) == [
            {"id": "1", "value": "alpha"},
            {"id": "2", "value": "beta"},
            {"id": "3", "value": "gamma"},
        ]


def test_combined_record_csvs_reject_header_drift(tmp_path) -> None:
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    output = tmp_path / "combined.csv"
    first.write_text("id,value\n1,alpha\n", encoding="utf-8")
    second.write_text("id,other\n2,beta\n", encoding="utf-8")

    with pytest.raises(ValueError, match="headers disagree"):
        _concatenate_csv_files(output, (first, second))


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
