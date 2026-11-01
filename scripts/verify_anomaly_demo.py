"""Verify every in-app anomaly demonstration scenario without holdout access."""

from __future__ import annotations

import json
import sys
import time
import tracemalloc
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.services.anomaly_detection import demo_scenario_options, run_demo_scenario


def verify_all_scenarios(employee_count: int = 120) -> dict[str, object]:
    rows = []
    tracemalloc.start()
    started = time.perf_counter()
    try:
        for option in demo_scenario_options(employee_count=employee_count):
            scenario_started = time.perf_counter()
            result = run_demo_scenario(
                option.index,
                employee_count=employee_count,
            )
            populations = {item.evaluation_count for item in result.comparisons}
            budgets = {item.review_count for item in result.comparisons}
            if len(populations) != 1 or len(budgets) != 1:
                raise AssertionError("comparison populations or review budgets differ")
            if any(
                item.employee_id not in result.evidence_by_employee_id
                for item in result.queue
            ):
                raise AssertionError("queue item has no source-history evidence")
            calculations = [
                calculation
                for evidence in result.evidence_by_employee_id.values()
                for calculation in evidence.calculations
            ]
            for calculation in calculations:
                adjusted = (
                    calculation.observed_service_months
                    + calculation.commendation_credit_months
                    - calculation.sanction_delay_months
                )
                if calculation.adjusted_service_months != adjusted:
                    raise AssertionError("policy arithmetic is inconsistent")
            rows.append({
                "scenario_id": option.scenario_id,
                "model_fit_count": result.model_fit_count,
                "validation_count": result.validation_count,
                "eligible_evaluation_count": result.eligible_test_count,
                "residual_evaluation_count": result.residual_test_count,
                "queue_count": len(result.queue),
                "comparison_population": populations.pop(),
                "review_capacity": budgets.pop(),
                "policy_calculation_count": len(calculations),
                "runtime_seconds": round(time.perf_counter() - scenario_started, 3),
            })
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return {
        "status": "verified",
        "data_class": "synthetic development demonstration",
        "holdout_accessed": False,
        "employee_count_per_scenario": employee_count,
        "model": "Isolation Forest",
        "model_estimators": 25,
        "review_budget_fraction": 0.10,
        "scenario_count": len(rows),
        "total_runtime_seconds": round(time.perf_counter() - started, 3),
        "peak_memory_mib": round(peak / (1024 * 1024), 3),
        "scenarios": rows,
    }


def main() -> int:
    print(json.dumps(verify_all_scenarios(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
