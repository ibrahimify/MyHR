"""Condition-balanced uncertainty for paired scenario-seed effects."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from statistics import mean, median, stdev
from typing import Mapping, Sequence

import numpy as np


@dataclass(frozen=True)
class ConditionBalancedSummary:
    """Paired effect summary with equal weight for each design condition."""

    condition_count: int
    seed_count: int
    condition_seed_counts: tuple[int, ...]
    effect_mean: float
    effect_median: float
    effect_std: float
    ci95_low: float
    ci95_high: float
    sign_flip_pvalue: float


def condition_balanced_paired_summary(
    deltas_by_condition: Mapping[str, Sequence[float]],
    *,
    seed: int,
    bootstrap_samples: int = 10_000,
    sign_flip_samples: int = 100_000,
) -> ConditionBalancedSummary:
    """Summarize paired seed effects without overweighting larger conditions."""

    if bootstrap_samples < 1 or sign_flip_samples < 1:
        raise ValueError("resampling samples must be positive")
    if not deltas_by_condition:
        raise ValueError("at least one condition is required")

    ordered = []
    for condition_id in sorted(deltas_by_condition):
        values = np.asarray(tuple(deltas_by_condition[condition_id]), dtype=float)
        if values.size == 0:
            raise ValueError(f"condition {condition_id} has no paired seed effects")
        if not np.isfinite(values).all():
            raise ValueError(f"condition {condition_id} contains non-finite effects")
        ordered.append(values)

    condition_means = [float(values.mean()) for values in ordered]
    rng = np.random.default_rng(seed)
    condition_count = len(ordered)
    selected_conditions = rng.integers(
        0,
        condition_count,
        size=(bootstrap_samples, condition_count),
    )
    sampled_means = np.empty_like(selected_conditions, dtype=float)
    for slot in range(condition_count):
        for condition_index, values in enumerate(ordered):
            selected_rows = np.flatnonzero(
                selected_conditions[:, slot] == condition_index
            )
            if selected_rows.size == 0:
                continue
            seed_indices = rng.integers(
                0,
                values.size,
                size=(selected_rows.size, values.size),
            )
            sampled_means[selected_rows, slot] = values[seed_indices].mean(axis=1)
    bootstrap_effects = sampled_means.mean(axis=1)
    ci_low, ci_high = np.quantile(bootstrap_effects, (0.025, 0.975))

    weighted_effects = np.concatenate([
        values / (condition_count * values.size)
        for values in ordered
    ])
    sign_flip_pvalue = _weighted_sign_flip_pvalue(
        weighted_effects,
        rng,
        sign_flip_samples,
    )
    return ConditionBalancedSummary(
        condition_count=condition_count,
        seed_count=sum(values.size for values in ordered),
        condition_seed_counts=tuple(int(values.size) for values in ordered),
        effect_mean=mean(condition_means),
        effect_median=median(condition_means),
        effect_std=stdev(condition_means) if condition_count > 1 else 0.0,
        ci95_low=float(ci_low),
        ci95_high=float(ci_high),
        sign_flip_pvalue=sign_flip_pvalue,
    )


def _weighted_sign_flip_pvalue(
    weighted_effects: np.ndarray,
    rng: np.random.Generator,
    samples: int,
) -> float:
    nonzero = weighted_effects[np.abs(weighted_effects) > 1e-15]
    if nonzero.size == 0:
        return 1.0
    observed = abs(float(nonzero.sum()))
    if nonzero.size <= 18:
        statistics = (
            abs(sum(sign * value for sign, value in zip(signs, nonzero)))
            for signs in product((-1.0, 1.0), repeat=int(nonzero.size))
        )
        total = 2 ** int(nonzero.size)
        return sum(value >= observed - 1e-15 for value in statistics) / total
    signs = rng.choice((-1.0, 1.0), size=(samples, nonzero.size))
    statistics = np.abs(signs @ nonzero)
    extreme = int(np.count_nonzero(statistics >= observed - 1e-15))
    return (extreme + 1) / (samples + 1)
