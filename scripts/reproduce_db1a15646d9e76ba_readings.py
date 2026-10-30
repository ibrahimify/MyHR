"""Read-only independent reproduction of three exploratory readings from
artifact db1a15646d9e76ba.

This script is deliberately standalone. It reads ONLY the artifact's raw CSV
files and recomputes:

  (a) the 8/72 rare-legitimate deterministic false-alert count;
  (b) which rare-legitimate mechanisms produced those flags;
  (c) the primary residual recall delta (fixed_review_budget) and its paired
      95% bootstrap confidence interval.

It does not import protocol_evaluation.py, the generator, or the auditor, so a
match provides evidence independent of those code paths. It never touches a
holdout path and writes nothing.

Usage:
    python scripts/reproduce_db1a15646d9e76ba_readings.py
"""

from __future__ import annotations

import csv
import statistics
from pathlib import Path
from random import Random

ARTIFACT = Path(
    "research_outputs/independent_development/independent_development_db1a15646d9e76ba"
)


def _read_csv(name: str) -> list[dict[str, str]]:
    with (ARTIFACT / name).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def reproduce_rare_legitimate_false_alerts() -> tuple[int, int, dict[str, int]]:
    """(a) and (b): count rare-legitimate records flagged by the deterministic
    policy rules, and attribute them to their rare-legitimate mechanism.

    A rare-legitimate record is identified from record_truth.csv
    (truth_category == 'rare_legitimate'). A deterministic flag is a
    record_predictions row with method 'deterministic_policy_rules' and
    predicted_anomaly truthy, at the rules_fixed operating point.
    """
    truth = _read_csv("record_truth.csv")
    predictions = _read_csv("record_predictions.csv")

    rare_by_key: dict[tuple[str, str], str] = {}
    for row in truth:
        if row["truth_category"] == "rare_legitimate":
            key = (row["scenario_id"], row["employee_id"])
            rare_by_key[key] = row["nominal_rare_pattern"] or row["realized_mechanism"]

    rare_total = len(rare_by_key)

    flagged_mechanisms: dict[str, int] = {}
    flagged_keys: set[tuple[str, str]] = set()
    for row in predictions:
        if row["method"] != "deterministic_policy_rules":
            continue
        if row.get("operating_point") not in {"rules_fixed", ""}:
            continue
        key = (row["scenario_id"], row["employee_id"])
        if key not in rare_by_key:
            continue
        predicted = row["predicted_anomaly"].strip().lower()
        if predicted in {"1", "true", "yes"}:
            if key in flagged_keys:
                continue
            flagged_keys.add(key)
            mechanism = rare_by_key[key]
            flagged_mechanisms[mechanism] = flagged_mechanisms.get(mechanism, 0) + 1

    return len(flagged_keys), rare_total, flagged_mechanisms


def reproduce_primary_recall_delta() -> tuple[float, tuple[float, float], int]:
    """(c): paired recall delta for the primary residual comparison at the
    fixed_review_budget operating point, with a paired bootstrap 95% CI.

    Pairs policy_matched vs raw_matched within each scenario for method
    'rule_negative_isolation_forest'. Recomputes recall per scenario from the
    stored TP/FN counts, takes the within-scenario difference, and bootstraps
    over scenarios.
    """
    rows = _read_csv("scenario_metrics.csv")

    def recall(tp: float, fn: float) -> float | None:
        denom = tp + fn
        return tp / denom if denom else None

    per_scenario: dict[str, dict[str, float | None]] = {}
    for row in rows:
        if row["method"] != "rule_negative_isolation_forest":
            continue
        if row["operating_point"] != "fixed_review_budget":
            continue
        rep = row["representation"]
        if rep not in {"policy_matched", "raw_matched"}:
            continue
        r = recall(float(row["true_positives"]), float(row["false_negatives"]))
        per_scenario.setdefault(row["scenario_id"], {})[rep] = r

    deltas: list[float] = []
    for scenario_id, reps in per_scenario.items():
        policy = reps.get("policy_matched")
        raw = reps.get("raw_matched")
        if policy is None or raw is None:
            continue  # zero-positive scenario: recall undefined, excluded
        deltas.append(policy - raw)

    if not deltas:
        return 0.0, (0.0, 0.0), 0

    mean_delta = statistics.fmean(deltas)

    # Paired scenario bootstrap, fixed seed for determinism.
    rng = Random(20261030)
    boot_means: list[float] = []
    n = len(deltas)
    for _ in range(10000):
        sample = [deltas[rng.randrange(n)] for _ in range(n)]
        boot_means.append(statistics.fmean(sample))
    boot_means.sort()
    lo = boot_means[int(0.025 * len(boot_means))]
    hi = boot_means[int(0.975 * len(boot_means))]
    return mean_delta, (lo, hi), n


def main() -> None:
    print(f"Independent read-only reproduction of {ARTIFACT.name}")
    print("=" * 70)

    flagged, total, mechanisms = reproduce_rare_legitimate_false_alerts()
    print("\n(a) Rare-legitimate deterministic false alerts")
    print(f"    reproduced: {flagged}/{total}")
    print("\n(b) Mechanisms that produced the flags")
    for mechanism, count in sorted(mechanisms.items()):
        print(f"    {mechanism}: {count}")

    mean_delta, (lo, hi), n = reproduce_primary_recall_delta()
    print("\n(c) Primary residual recall delta (fixed_review_budget)")
    print(f"    eligible paired scenarios: {n}")
    print(f"    recall delta mean: {mean_delta:+.4f}")
    print(f"    paired bootstrap 95% CI: [{lo:+.4f}, {hi:+.4f}]")


if __name__ == "__main__":
    main()
