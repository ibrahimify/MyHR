"""Semantic regression tests for the two development-only generators."""

from __future__ import annotations

import unittest

from src.research.independent_scenarios import (
    IndependentEventKind,
    TruthCategory,
    generate_independent_world,
    independent_scenario_matrix,
)
from src.services.anomaly_detection import synthetic_data as syn
from src.services.anomaly_detection.scenario_generation import (
    generate_scenario_dataset,
    scenario_matrix,
)


MIN_PLAUSIBLE_HIRE_AGE = 18.0


def _age_at_hire(date_of_birth, hire_date) -> float:
    return (hire_date - date_of_birth).days / 365.2425


class IndependentGeneratorSemanticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worlds = tuple(
            generate_independent_world(spec)
            for spec in independent_scenario_matrix(360)
        )

    def test_birth_and_hire_dates_form_plausible_pairs(self):
        offenders = []
        for world in self.worlds:
            for employee in world.employees:
                age = _age_at_hire(employee.date_of_birth, employee.hire_date)
                if age < MIN_PLAUSIBLE_HIRE_AGE:
                    offenders.append(
                        (world.spec.scenario_id, employee.employee_id, age)
                    )
        self.assertEqual(offenders, [])

    def test_truth_causal_events_match_visible_or_omitted_interventions(self):
        offenders = []
        for world in self.worlds:
            employees = {employee.employee_id: employee for employee in world.employees}
            for truth in world.truth:
                employee = employees[truth.employee_id]
                visible_ids = {event.event_id for event in employee.events}
                causal_ids = {event.event_id for event in truth.causal_events}

                if truth.category is TruthCategory.ORDINARY_LEGITIMATE:
                    if truth.mechanism != "none" or causal_ids:
                        offenders.append((world.spec.scenario_id, truth.employee_id, "ordinary"))
                    continue

                if not causal_ids:
                    offenders.append((world.spec.scenario_id, truth.employee_id, "empty"))
                    continue

                if truth.mechanism == "missing_increment_import":
                    if causal_ids & visible_ids:
                        offenders.append((world.spec.scenario_id, truth.employee_id, "omission-visible"))
                elif not causal_ids <= visible_ids:
                    offenders.append((world.spec.scenario_id, truth.employee_id, "causal-not-visible"))

                if (
                    truth.category is TruthCategory.RARE_LEGITIMATE
                    and truth.realized_mechanism != truth.mechanism
                ):
                    offenders.append((world.spec.scenario_id, truth.employee_id, "mechanism-mismatch"))
        self.assertEqual(offenders, [])

    def test_lawful_exception_causal_events_do_not_predate_hire(self):
        offenders = []
        for world in self.worlds:
            employees = {employee.employee_id: employee for employee in world.employees}
            for truth in world.truth:
                if truth.category is not TruthCategory.RARE_LEGITIMATE:
                    continue
                employee = employees[truth.employee_id]
                for event in truth.causal_events:
                    if event.effective_date < employee.hire_date:
                        offenders.append(
                            (world.spec.scenario_id, truth.employee_id, event.event_id)
                        )
                    if (
                        event.kind is IndependentEventKind.PROMOTION
                        and event.level_before == event.level_after
                    ):
                        offenders.append(
                            (world.spec.scenario_id, truth.employee_id, "no-op-promotion")
                        )
        self.assertEqual(offenders, [])


class OriginalGeneratorSemanticTests(unittest.TestCase):
    @staticmethod
    def _dataset(seed: int, employee_count: int = 1000) -> syn.SyntheticDataset:
        return syn.generate_synthetic_dataset(
            syn.ExperimentConfig(
                seed=seed,
                employee_count=employee_count,
                anomaly_rate=0.10,
                rare_legitimate_rate=0.04,
            )
        )

    def test_birth_and_hire_dates_survive_identity_mutations(self):
        offenders = []
        for seed in (2026, 2027, 2028):
            for record in self._dataset(seed).records:
                age = _age_at_hire(record.identity.date_of_birth, record.hire_date)
                if age < MIN_PLAUSIBLE_HIRE_AGE:
                    offenders.append((seed, record.identity.employee_id, age))
        self.assertEqual(offenders, [])

    def test_duplicate_identity_and_history_stay_in_one_partition(self):
        for seed in (2026, 2027, 2028):
            dataset = self._dataset(seed)
            records = {record.identity.employee_id: record for record in dataset.records}
            for duplicate in dataset.records:
                if duplicate.duplicate_of_employee_id is None:
                    continue
                source = records[duplicate.duplicate_of_employee_id]
                self.assertEqual(duplicate.split, source.split)
                self.assertEqual(duplicate.latent_person_id, source.latent_person_id)
                self.assertEqual(duplicate.hire_date, source.hire_date)
                self.assertEqual(duplicate.events, source.events)
                self.assertEqual(duplicate.department, source.department)
                self.assertEqual(duplicate.role, source.role)
                self.assertEqual(duplicate.employment_track, source.employment_track)

    def test_every_hard_nonduplicate_kind_is_traceable_in_test(self):
        expected_kinds = set(syn.HardNonduplicateKind)
        for seed in (2026, 2027, 2028):
            dataset = self._dataset(seed)
            records = {record.identity.employee_id: record for record in dataset.records}
            hard_records = [
                record for record in dataset.records
                if record.hard_nonduplicate_kind is not None
            ]
            self.assertEqual(
                {record.hard_nonduplicate_kind for record in hard_records},
                expected_kinds,
            )
            for target in hard_records:
                anchor = records[target.hard_nonduplicate_anchor_id]
                self.assertEqual(target.split, syn.DatasetSplit.TEST)
                self.assertEqual(anchor.split, syn.DatasetSplit.TEST)
                self.assertIsNone(target.latent_person_id)
                self.assertIsNone(anchor.latent_person_id)
                self.assertIsNone(target.duplicate_of_employee_id)
                self.assertIsNone(anchor.duplicate_of_employee_id)
                if target.hard_nonduplicate_kind is syn.HardNonduplicateKind.SIMILAR_NAME:
                    self.assertEqual(
                        target.identity.full_name.split()[0],
                        anchor.identity.full_name.split()[0],
                    )
                elif target.hard_nonduplicate_kind is syn.HardNonduplicateKind.SHARED_BIRTHDAY:
                    self.assertEqual(
                        target.identity.date_of_birth,
                        anchor.identity.date_of_birth,
                    )
                elif target.hard_nonduplicate_kind is syn.HardNonduplicateKind.RELATIVE:
                    self.assertEqual(
                        target.identity.full_name.split()[-1],
                        anchor.identity.full_name.split()[-1],
                    )
                elif target.hard_nonduplicate_kind is syn.HardNonduplicateKind.NEAR_IDENTICAL_ID:
                    self.assertEqual(
                        target.identity.national_id,
                        syn._transpose_identifier(anchor.identity.national_id),
                    )


class ProtocolV2GeneratorSemanticTests(unittest.TestCase):
    def test_all_generated_identities_are_adults_at_hire(self):
        offenders = []
        for config in scenario_matrix("development", count=12, employee_count=120):
            dataset = generate_scenario_dataset(config).dataset
            for record in dataset.records:
                age = _age_at_hire(record.identity.date_of_birth, record.hire_date)
                if age < MIN_PLAUSIBLE_HIRE_AGE:
                    offenders.append((config.scenario_id, record.identity.employee_id, age))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
