import ast
import re
import unittest
from dataclasses import replace
from pathlib import Path

from src.research.independent_scenario_adapter import adapt_independent_world
from src.research.independent_scenarios import (
    IndependentScenarioSpec,
    IndependentSplit,
    TruthCategory,
    anomaly_mechanisms,
    generate_independent_world,
    independent_scenario_matrix,
    population_families,
)
from src.services.anomaly_detection.deterministic_checks import validate_record_with_policy


class IndependentScenarioTests(unittest.TestCase):
    def test_generator_has_no_detector_or_existing_generator_imports(self):
        source = Path("src/research/independent_scenarios.py").read_text(encoding="utf-8")
        imported_roots = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])

        self.assertNotIn("src", imported_roots)

    def test_matrix_covers_three_populations_and_four_causal_mechanisms(self):
        specs = independent_scenario_matrix(employee_count=120)

        self.assertEqual(len(specs), 12)
        self.assertEqual({spec.population for spec in specs}, set(population_families()))
        self.assertEqual({spec.mechanism for spec in specs}, set(anomaly_mechanisms()))
        self.assertTrue(all(spec.run_purpose == "independent_development" for spec in specs))

    def test_holdout_purpose_is_not_defined(self):
        spec = replace(independent_scenario_matrix(employee_count=120)[0], run_purpose="holdout")

        with self.assertRaisesRegex(ValueError, "development-only"):
            generate_independent_world(spec)

    def test_generation_is_reproducible_and_truth_is_separate(self):
        spec = independent_scenario_matrix(employee_count=120)[0]

        first = generate_independent_world(spec)
        second = generate_independent_world(spec)

        self.assertEqual(first, second)
        self.assertEqual(
            {employee.employee_id for employee in first.employees},
            {entry.employee_id for entry in first.truth},
        )
        for employee in first.employees:
            for event in employee.events:
                self.assertIsNotNone(re.fullmatch(r"EV-[0-9a-f]{14}", event.event_id))

    def test_each_split_contains_errors_and_rare_legitimate_histories(self):
        world = generate_independent_world(independent_scenario_matrix(employee_count=120)[0])
        split_by_employee = {
            employee.employee_id: employee.split for employee in world.employees
        }

        for split in IndependentSplit:
            categories = {
                entry.category for entry in world.truth
                if split_by_employee[entry.employee_id] is split
            }
            self.assertIn(TruthCategory.RARE_LEGITIMATE, categories)
            self.assertTrue(any(category not in {
                TruthCategory.ORDINARY_LEGITIMATE,
                TruthCategory.RARE_LEGITIMATE,
            } for category in categories))

    def test_adapter_preserves_residual_errors_for_incremental_evaluation(self):
        specs = [
            spec for spec in independent_scenario_matrix(employee_count=120)
            if spec.mechanism in {"wrong_employee_link", "missing_increment_import"}
        ]
        residual_error_count = 0
        for spec in specs:
            scenario = adapt_independent_world(generate_independent_world(spec))
            for record in scenario.dataset.records:
                if not record.has_progression_anomaly:
                    continue
                if not validate_record_with_policy(record, scenario.policy):
                    residual_error_count += 1

        self.assertGreater(residual_error_count, 0)


if __name__ == "__main__":
    unittest.main()
