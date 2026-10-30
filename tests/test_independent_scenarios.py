import ast
import json
import re
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from src.research.independent_scenario_adapter import adapt_independent_world
from src.research.independent_scenarios import (
    REFERENCE_DATE,
    IndependentEventKind,
    IndependentScenarioSpec,
    IndependentSplit,
    TruthCategory,
    anomaly_mechanisms,
    compatible_rare_patterns_by_population,
    generate_independent_world,
    independent_scenario_matrix,
    population_families,
)
from src.services.anomaly_detection.deterministic_checks import validate_record_with_policy
from scripts.run_tdk_independent_development import (
    _event_ledger_rows,
    _policy_epoch_rows,
    _require_primary_policy_signal,
    _record_truth_rows,
    _staged_artifact_directory,
)
from scripts.run_tdk_protocol_experiment import _write_csv
from scripts.audit_tdk_protocol_artifact import _verify_truth_sidecars


class IndependentScenarioTests(unittest.TestCase):
    def test_compatible_rare_patterns_are_explicit_for_every_population(self):
        compatibility = compatible_rare_patterns_by_population()

        self.assertEqual(set(compatibility), set(population_families()))
        self.assertIn("policy_transition", compatibility["stable_administration"])
        self.assertIn("policy_transition", compatibility["merger_migration"])
        self.assertNotIn("policy_transition", compatibility["rapid_expansion"])

    def test_incompatible_population_pattern_pair_is_rejected(self):
        spec = IndependentScenarioSpec(
            scenario_id="incompatible-transition",
            run_purpose="independent_development",
            seed=1,
            split_seed=2,
            model_seed=3,
            employee_count=120,
            population="rapid_expansion",
            mechanism="wrong_employee_link",
            rare_pattern="policy_transition",
        )

        with self.assertRaisesRegex(ValueError, "incompatible scenario combination"):
            spec.validate()

    def test_primary_feature_guard_rejects_family_wide_policy_collapse(self):
        row = {
            "method": "rule_negative_isolation_forest",
            "representation": "policy_matched",
            "operating_point": "fixed_review_budget",
            "policy_signal_nonconstant_feature_count": 0,
        }

        with self.assertRaisesRegex(RuntimeError, "constant"):
            _require_primary_policy_signal([row])

        _require_primary_policy_signal([
            {**row, "policy_signal_nonconstant_feature_count": 1}
        ])

    def test_staged_artifact_is_published_only_after_success(self):
        with tempfile.TemporaryDirectory() as directory:
            final_dir = Path(directory) / "artifact_123"

            with _staged_artifact_directory(final_dir) as staging_dir:
                self.assertNotEqual(staging_dir, final_dir)
                self.assertFalse(final_dir.exists())
                (staging_dir / "manifest.json").write_text("{}", encoding="utf-8")

            self.assertTrue((final_dir / "manifest.json").is_file())
            self.assertFalse(staging_dir.exists())
            self.assertEqual(list(Path(directory).iterdir()), [final_dir])

    def test_failed_artifact_removes_only_its_staging_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            final_dir = root / "artifact_123"
            unrelated = root / ".artifact_other.staging-preserve"
            unrelated.mkdir()

            with self.assertRaisesRegex(RuntimeError, "simulated failure"):
                with _staged_artifact_directory(final_dir) as staging_dir:
                    (staging_dir / "partial.csv").write_text("partial", encoding="utf-8")
                    raise RuntimeError("simulated failure")

            self.assertFalse(final_dir.exists())
            self.assertFalse(staging_dir.exists())
            self.assertTrue(unrelated.is_dir())

    def test_failed_artifact_can_be_retried_with_same_final_name(self):
        with tempfile.TemporaryDirectory() as directory:
            final_dir = Path(directory) / "artifact_123"

            with self.assertRaises(RuntimeError):
                with _staged_artifact_directory(final_dir) as staging_dir:
                    (staging_dir / "partial.csv").write_text("partial", encoding="utf-8")
                    raise RuntimeError("simulated failure")

            with _staged_artifact_directory(final_dir) as staging_dir:
                (staging_dir / "manifest.json").write_text("complete", encoding="utf-8")

            self.assertEqual(
                (final_dir / "manifest.json").read_text(encoding="utf-8"),
                "complete",
            )

    def test_completed_artifact_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            final_dir = Path(directory) / "artifact_123"
            final_dir.mkdir()
            marker = final_dir / "manifest.json"
            marker.write_text("original", encoding="utf-8")

            with self.assertRaisesRegex(FileExistsError, "Artifact already exists"):
                with _staged_artifact_directory(final_dir):
                    self.fail("existing artifact must be rejected before staging")

            self.assertEqual(marker.read_text(encoding="utf-8"), "original")
            self.assertEqual(list(Path(directory).iterdir()), [final_dir])

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
        self.assertEqual(
            {(spec.population, spec.mechanism) for spec in specs},
            {
                (population, mechanism)
                for population in population_families()
                for mechanism in anomaly_mechanisms()
            },
        )
        self.assertTrue(all(spec.run_purpose == "independent_development" for spec in specs))

    def test_every_error_realizes_its_declared_mechanism_without_known_confounds(self):
        for spec in independent_scenario_matrix(employee_count=120):
            world = generate_independent_world(spec)
            employees = {employee.employee_id: employee for employee in world.employees}
            errors = [
                entry for entry in world.truth
                if entry.category not in {
                    TruthCategory.ORDINARY_LEGITIMATE,
                    TruthCategory.RARE_LEGITIMATE,
                }
            ]
            self.assertTrue(errors, spec.scenario_id)
            for entry in errors:
                self.assertEqual(entry.realized_mechanism, spec.mechanism)
                self.assertTrue(entry.causal_events)
                if spec.mechanism == "missing_increment_import":
                    employee_event_ids = {
                        event.event_id for event in employees[entry.employee_id].events
                    }
                    self.assertTrue(all(
                        event.kind is IndependentEventKind.SALARY_INCREMENT
                        and event.event_id not in employee_event_ids
                        for event in entry.causal_events
                    ))
                elif spec.mechanism == "approval_bypass":
                    employee = employees[entry.employee_id]
                    self.assertEqual(employee.track.value, "progression")
                    for event in entry.causal_events:
                        self.assertIsNone(event.approval_reference)
                        self.assertEqual(event.approval_status, "bypassed")
                        service_months = (
                            (event.effective_date.year - employee.hire_date.year) * 12
                            + event.effective_date.month - employee.hire_date.month
                        )
                        self.assertGreaterEqual(service_months, 36)
            if spec.mechanism == "approval_bypass":
                scenario = adapt_independent_world(world)
                error_ids = {entry.employee_id for entry in errors}
                for record in scenario.dataset.records:
                    if record.identity.employee_id not in error_ids:
                        continue
                    codes = {
                        finding.code for finding in validate_record_with_policy(
                            record, scenario.policy, scenario.policy_epochs
                        )
                    }
                    self.assertIn("promotion_approval_bypassed", codes)
                    self.assertNotIn("promotion_policy_service_deficit", codes)
                    self.assertNotIn("promotion_on_other_track", codes)

    def test_observable_events_do_not_extend_beyond_reference_date(self):
        for spec in independent_scenario_matrix(employee_count=120):
            world = generate_independent_world(spec)
            for employee in world.employees:
                for event in employee.events:
                    self.assertLessEqual(event.effective_date, REFERENCE_DATE)
                    self.assertLessEqual(event.recorded_date, REFERENCE_DATE)

    def test_ordinary_legitimate_histories_include_realistic_event_variety(self):
        worlds = [
            generate_independent_world(spec)
            for spec in independent_scenario_matrix(employee_count=120)
        ]
        truth_by_world = [
            {entry.employee_id: entry for entry in world.truth}
            for world in worlds
        ]
        ordinary_events = [
            event
            for world, truth_by_employee in zip(worlds, truth_by_world)
            for employee in world.employees
            if truth_by_employee[employee.employee_id].category
            is TruthCategory.ORDINARY_LEGITIMATE
            for event in employee.events
        ]

        self.assertTrue(any(
            event.kind is IndependentEventKind.COMMENDATION
            for event in ordinary_events
        ))
        self.assertTrue(any(
            event.kind is IndependentEventKind.SANCTION
            for event in ordinary_events
        ))
        ordinary_review_counts = [
            sum(
                event.kind is IndependentEventKind.PERFORMANCE_REVIEW
                for event in employee.events
            )
            for world, truth_by_employee in zip(worlds, truth_by_world)
            for employee in world.employees
            if truth_by_employee[employee.employee_id].category
            is TruthCategory.ORDINARY_LEGITIMATE
        ]
        self.assertTrue(any(count > 1 for count in ordinary_review_counts))

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
        omission_rows = [
            row for row in truth_with_omission
            if row["nominal_anomaly_mechanism"] == "missing_increment_import"
            and row["truth_category"] not in {
                TruthCategory.ORDINARY_LEGITIMATE.value,
                TruthCategory.RARE_LEGITIMATE.value,
            }
        ]
        self.assertTrue(omission_rows)
        self.assertTrue(all(
            all(
                event["ledger_status"] == "omitted"
                for event in json.loads(row["causal_events_json"])
            )
            for row in omission_rows
        ))

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


class LateCorrectionAndPolicyTransitionScenarioTests(unittest.TestCase):
    """Verify the late_correction and policy_transition rare-legitimate patterns."""

    def _spec(self, rare_pattern: str, seed: int = 99001) -> IndependentScenarioSpec:
        return IndependentScenarioSpec(
            scenario_id=f"test-{rare_pattern}",
            run_purpose="independent_development",
            seed=seed,
            split_seed=seed + 2,
            model_seed=seed + 6,
            employee_count=120,
            population=population_families()[0],
            mechanism=anomaly_mechanisms()[0],
            rare_pattern=rare_pattern,
        )

    # --- late_correction ---

    def test_late_correction_spec_validates(self):
        self._spec("late_correction").validate()

    def test_late_correction_generates_rare_legitimate_records(self):
        world = generate_independent_world(self._spec("late_correction"))
        rare = [t for t in world.truth if t.category.value == "rare_legitimate"]
        self.assertGreater(len(rare), 0, "late_correction must produce rare-legitimate records")

    def test_late_correction_causal_events_have_correction_link(self):
        world = generate_independent_world(self._spec("late_correction"))
        rare = [t for t in world.truth if t.category.value == "rare_legitimate"]
        correction_events = [
            e for t in rare for e in t.causal_events
            if e.correction_of_event_id is not None
        ]
        self.assertGreater(
            len(correction_events), 0,
            "late_correction causal events must include at least one correction_of_event_id link",
        )

    def test_late_correction_erroneous_events_are_in_ledger(self):
        """The erroneous pre-correction event must appear in the employee ledger."""
        world = generate_independent_world(self._spec("late_correction"))
        rare_employee_ids = {
            t.employee_id for t in world.truth if t.category.value == "rare_legitimate"
        }
        for emp in world.employees:
            if emp.employee_id not in rare_employee_ids:
                continue
            event_ids = {e.event_id for e in emp.events}
            correction_links = {
                e.correction_of_event_id for e in emp.events if e.correction_of_event_id
            }
            for linked_id in correction_links:
                self.assertIn(
                    linked_id, event_ids,
                    f"correction_of_event_id {linked_id!r} not in ledger for {emp.employee_id}",
                )

    def test_late_correction_rare_legitimate_not_flagged_by_invariant_rules(self):
        world = generate_independent_world(self._spec("late_correction"))
        scenario = adapt_independent_world(world)
        rare_ids = {
            t.employee_id for t in world.truth if t.category.value == "rare_legitimate"
        }
        from src.services.anomaly_detection.deterministic_checks import validate_invariant_record
        for record in scenario.dataset.records:
            if record.identity.employee_id in rare_ids:
                findings = validate_invariant_record(record)
                self.assertEqual(
                    len(findings), 0,
                    f"rare-legitimate {record.identity.employee_id} flagged by invariant rules: {findings}",
                )

    def test_late_correction_policy_assessment_does_not_raise(self):
        """Regression: assess_promotion_history must not raise on a superseded,
        re-dated erroneous promotion event (policy epoch boundary bug)."""
        from src.services.anomaly_detection.policy_history import assess_promotion_history
        world = generate_independent_world(self._spec("late_correction"))
        scenario = adapt_independent_world(world)
        for record in scenario.dataset.records:
            # Must not raise ValueError about inapplicable policy.
            assess_promotion_history(record, scenario.policy, scenario.policy_epochs)

    def test_late_correction_superseded_event_excluded_from_assessment(self):
        """A promotion superseded by a correction must not be assessed twice."""
        from src.services.anomaly_detection.policy_history import assess_promotion_history
        world = generate_independent_world(self._spec("late_correction"))
        scenario = adapt_independent_world(world)
        rare_ids = {
            t.employee_id for t in world.truth if t.category.value == "rare_legitimate"
        }
        for record in scenario.dataset.records:
            if record.identity.employee_id not in rare_ids:
                continue
            superseded = {
                e.correction_of_source_id
                for e in record.events
                if e.correction_of_source_id is not None
            }
            if not superseded:
                continue
            assessments = assess_promotion_history(record, scenario.policy, scenario.policy_epochs)
            assessed_ids = {a.event_source_id for a in assessments}
            for superseded_id in superseded:
                self.assertNotIn(
                    superseded_id, assessed_ids,
                    f"superseded event {superseded_id} was assessed for {record.identity.employee_id}",
                )

    # --- policy_transition ---

    def test_policy_transition_spec_validates(self):
        self._spec("policy_transition").validate()

    def test_policy_transition_generates_rare_legitimate_records(self):
        world = generate_independent_world(self._spec("policy_transition"))
        rare = [t for t in world.truth if t.category.value == "rare_legitimate"]
        self.assertGreater(len(rare), 0, "policy_transition must produce rare-legitimate records")

    def test_policy_transition_causal_events_use_legacy_policy(self):
        world = generate_independent_world(self._spec("policy_transition"))
        rare = [t for t in world.truth if t.category.value == "rare_legitimate"]
        legacy_events = [
            e for t in rare for e in t.causal_events
            if e.policy_id == "legacy-pre-2023"
        ]
        self.assertGreater(
            len(legacy_events), 0,
            "policy_transition causal events must reference legacy-pre-2023 policy",
        )

    def test_policy_transition_rare_legitimate_not_flagged_by_invariant_rules(self):
        world = generate_independent_world(self._spec("policy_transition"))
        scenario = adapt_independent_world(world)
        rare_ids = {
            t.employee_id for t in world.truth if t.category.value == "rare_legitimate"
        }
        from src.services.anomaly_detection.deterministic_checks import validate_invariant_record
        for record in scenario.dataset.records:
            if record.identity.employee_id in rare_ids:
                findings = validate_invariant_record(record)
                self.assertEqual(
                    len(findings), 0,
                    f"rare-legitimate {record.identity.employee_id} flagged by invariant rules: {findings}",
                )

    def test_all_five_rare_patterns_are_registered(self):
        from src.research.independent_scenarios import rare_legitimate_patterns
        patterns = rare_legitimate_patterns()
        for expected in (
            "grandfathered_policy", "recognized_prior_service",
            "delayed_bulk_recording", "late_correction", "policy_transition",
        ):
            self.assertIn(expected, patterns, f"pattern {expected!r} missing from rare_legitimate_patterns()")


class EntitlementEvidenceScenarioTests(unittest.TestCase):
    def _world(self):
        spec = IndependentScenarioSpec(
            scenario_id="test-grandfathered-evidence",
            run_purpose="independent_development",
            seed=99101,
            split_seed=99103,
            model_seed=99107,
            employee_count=120,
            population="stable_administration",
            mechanism="wrong_employee_link",
            rare_pattern="grandfathered_policy",
        )
        return generate_independent_world(spec)

    def test_every_grandfathered_case_has_event_specific_entitlement(self):
        world = self._world()
        rare_entries = {
            entry.employee_id: entry
            for entry in world.truth
            if entry.category is TruthCategory.RARE_LEGITIMATE
        }
        evidence_by_employee = {
            evidence.employee_id: evidence for evidence in world.entitlement_evidence
        }

        self.assertEqual(set(evidence_by_employee), set(rare_entries))
        for employee_id, truth in rare_entries.items():
            self.assertEqual(len(truth.causal_events), 1)
            promotion = truth.causal_events[0]
            evidence = evidence_by_employee[employee_id]
            self.assertEqual(evidence.policy_id, "legacy-pre-2023")
            self.assertEqual(evidence.policy_version, "1.0")
            self.assertEqual(evidence.relevant_event_id, promotion.event_id)
            self.assertLessEqual(evidence.recorded_at, promotion.recorded_date)
            self.assertTrue(evidence.evidence_reference)

    def test_adapter_preserves_entitlement_identity_and_event_linkage(self):
        world = self._world()
        scenario = adapt_independent_world(world)

        for evidence in world.entitlement_evidence:
            adapted = scenario.population.grandfathering_evidence_by_employee_id[
                evidence.employee_id
            ]
            self.assertEqual(len(adapted), 1)
            self.assertEqual(adapted[0].employee_id, evidence.employee_id)
            self.assertEqual(adapted[0].policy_id, evidence.policy_id)
            self.assertEqual(adapted[0].policy_version, evidence.policy_version)
            self.assertEqual(adapted[0].event_source_id, evidence.relevant_event_id)

    def test_generated_entitlement_satisfies_strict_policy_assessment(self):
        from src.services.anomaly_detection.policy_history import assess_promotion_history

        world = self._world()
        scenario = adapt_independent_world(world)
        rare_ids = {
            entry.employee_id
            for entry in world.truth
            if entry.category is TruthCategory.RARE_LEGITIMATE
        }
        for record in scenario.dataset.records:
            employee_id = record.identity.employee_id
            if employee_id not in rare_ids:
                continue
            evidence = (
                scenario.population.grandfathering_evidence_by_employee_id[
                    employee_id
                ]
            )
            assessments = assess_promotion_history(
                record,
                scenario.policy,
                scenario.policy_epochs,
                grandfathering_evidence=evidence,
            )
            self.assertEqual(len(assessments), 1)

    def test_protocol_evaluation_consumes_generated_entitlement(self):
        from src.services.anomaly_detection.protocol_evaluation import evaluate_scenario

        scenario = adapt_independent_world(self._world())
        result = evaluate_scenario(scenario)
        policy_rows = [
            row for row in result.metric_rows
            if row["method"] == "deterministic_policy_rules"
            and row["operating_point"] == "rules_fixed"
        ]

        self.assertEqual(len(policy_rows), 1)
        self.assertEqual(policy_rows[0]["rare_legitimate_flagged"], 0)
