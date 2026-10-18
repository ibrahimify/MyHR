import ast
import json
import re
import tempfile
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
from scripts.run_tdk_independent_development import (
    _event_ledger_rows,
    _policy_epoch_rows,
    _record_truth_rows,
)
from scripts.run_tdk_protocol_experiment import _write_csv
from scripts.audit_tdk_protocol_artifact import _verify_truth_sidecars


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

    def test_truth_ledger_preserves_realized_mechanism_and_causal_events(self):
        spec = next(
            item for item in independent_scenario_matrix(employee_count=120)
            if item.rare_pattern == "grandfathered_policy"
        )
        world = generate_independent_world(spec)
        employees = {employee.employee_id: employee for employee in world.employees}
        rare_entries = [
            entry for entry in world.truth
            if entry.category is TruthCategory.RARE_LEGITIMATE
        ]

        self.assertTrue(rare_entries)
        for entry in rare_entries:
            self.assertEqual(entry.track, employees[entry.employee_id].track)
            self.assertTrue(entry.causal_events)
            expected = (
                "grandfathered_policy"
                if entry.track.value == "progression"
                else "delayed_bulk_recording"
            )
            self.assertEqual(entry.mechanism, spec.rare_pattern)
            self.assertEqual(entry.realized_mechanism, expected)

        truth_rows = {
            row["employee_id"]: row for row in _record_truth_rows(world)
        }
        sample = truth_rows[rare_entries[0].employee_id]
        causal_events = json.loads(sample["causal_events_json"])
        self.assertEqual(
            sample["realized_mechanism"], rare_entries[0].realized_mechanism
        )
        self.assertEqual(sample["employment_track"], rare_entries[0].track.value)
        self.assertTrue(sample["department"])
        self.assertTrue(sample["role"])
        self.assertTrue(sample["date_of_birth"])
        self.assertTrue(sample["hire_date"])
        self.assertTrue(causal_events)
        self.assertIn("effective_date", causal_events[0])
        self.assertIn("recorded_date", causal_events[0])
        self.assertEqual(len(truth_rows), len(world.employees))

        event_rows = _event_ledger_rows(world)
        policy_rows = _policy_epoch_rows(world)
        known_policies = {row["policy_id"] for row in policy_rows}
        self.assertTrue(event_rows)
        self.assertTrue(all(row["policy_id"] in known_policies for row in event_rows))
        self.assertTrue(all(row["effective_date"] for row in event_rows))
        self.assertTrue(all(row["recorded_date"] for row in event_rows))
        self.assertTrue(all("category" in row for row in event_rows))
        self.assertTrue(all("resolved_date" in row for row in event_rows))

        world_with_omission = generate_independent_world(next(
            item for item in independent_scenario_matrix(employee_count=120)
            if item.mechanism == "missing_increment_import"
        ))
        truth_with_omission = _record_truth_rows(world_with_omission)
        causal_events = [
            event
            for row in truth_with_omission
            for event in json.loads(row["causal_events_json"])
        ]
        self.assertTrue(any(event["ledger_status"] == "omitted" for event in causal_events))

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

    def test_generated_sidecars_pass_independent_provenance_audit(self):
        world = generate_independent_world(independent_scenario_matrix(employee_count=120)[1])
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            _write_csv(run_dir / "record_truth.csv", _record_truth_rows(world))
            _write_csv(run_dir / "administrative_events.csv", _event_ledger_rows(world))
            _write_csv(run_dir / "policy_epochs.csv", _policy_epoch_rows(world))
            predictions = [{
                "scenario_id": world.spec.scenario_id,
                "employee_id": employee.employee_id,
            } for employee in world.employees if employee.split.value == "test"]

            result = _verify_truth_sidecars(run_dir, predictions, required=True)

        self.assertTrue(result["present"])
        self.assertEqual(result["record_truth_rows"], len(world.employees))


if __name__ == "__main__":
    unittest.main()
