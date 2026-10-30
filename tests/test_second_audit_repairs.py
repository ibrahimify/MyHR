"""Regression tests for confirmed second-audit findings (2026-10-30).

These tests encode the SEMANTIC contracts that the earlier metadata-only tests
failed to check. See docs/TDK_SECOND_EXTERNAL_AUDIT_2026-10-30.md.

They are written to FAIL against revision 4ee488b and pass only after the
corresponding fix:

  R1 — duplicate ground truth: a duplicate and its linked source must both be
       derived from the SAME latent person (shared identity facts), not merely
       share a latent_person_id tag.
  R6 — candidate-set confusion counts must conserve the candidate universe:
       TP + FP + TN + FN must equal the candidate-pair count exactly.
"""

import unittest
from unittest.mock import patch

import src.services.anomaly_detection.synthetic_data as syn
from src.services.anomaly_detection.duplicate_detection import (
    confusion_counts_for_pairs,
)


class R1DuplicateIdentityDerivationTests(unittest.TestCase):
    """R1: the source of each duplicate must share the latent person's identity."""

    def _generate_with_latent_capture(self, seed: int = 2026, n: int = 1000):
        latent: dict[str, syn.LatentPerson] = {}
        original = syn._generate_latent_person

        def capture(index, rng):
            person = original(index, rng)
            latent[person.latent_person_id] = person
            return person

        with patch.object(syn, "_generate_latent_person", side_effect=capture):
            dataset = syn.generate_synthetic_dataset(
                syn.ExperimentConfig(
                    seed=seed, employee_count=n,
                    anomaly_rate=0.10, rare_legitimate_rate=0.04,
                )
            )
        return dataset, latent

    def test_source_identity_is_derived_from_shared_latent_person(self):
        dataset, latent = self._generate_with_latent_capture()
        by_id = {r.identity.employee_id: r for r in dataset.records}
        duplicates = [r for r in dataset.records if r.duplicate_of_employee_id]
        self.assertGreater(len(duplicates), 0, "need at least one duplicate")
        for dup in duplicates:
            source = by_id[dup.duplicate_of_employee_id]
            person = latent[dup.latent_person_id]
            # The source must BE the canonical identity of the latent person:
            # same name, DOB, national id, email. A shared tag is not enough.
            self.assertEqual(
                (
                    source.identity.full_name,
                    source.identity.date_of_birth,
                    source.identity.national_id,
                    source.identity.email,
                ),
                (
                    person.full_name,
                    person.date_of_birth,
                    person.national_id,
                    person.email,
                ),
                f"source {source.identity.employee_id} of duplicate "
                f"{dup.identity.employee_id} is not derived from latent "
                f"{person.latent_person_id}",
            )

    def test_duplicate_and_source_are_the_same_person_by_facts(self):
        """The duplicate variant must be a recognizable corruption of its source:
        at least one strong identity field (name, DOB, or national id) must still
        match or near-match, so the pair is a genuine same-person pair."""
        dataset, latent = self._generate_with_latent_capture()
        by_id = {r.identity.employee_id: r for r in dataset.records}
        for dup in dataset.records:
            if not dup.duplicate_of_employee_id:
                continue
            source = by_id[dup.duplicate_of_employee_id]
            person = latent[dup.latent_person_id]
            # Both derive from `person`; at least one of DOB / national-id root /
            # family name should trace to the same latent facts.
            shared_dob = dup.identity.date_of_birth == person.date_of_birth or (
                source.identity.date_of_birth == person.date_of_birth
            )
            shared_family = (
                person.full_name.split()[-1] in dup.identity.full_name
                or person.full_name.split()[-1] in source.identity.full_name
            )
            self.assertTrue(
                shared_dob or shared_family,
                f"duplicate {dup.identity.employee_id} shares no latent facts with "
                f"its source {source.identity.employee_id}",
            )

    def test_true_pairs_are_scorable_by_at_least_one_matcher(self):
        """With correct identities, the similarity matcher should recover at least
        one true duplicate pair in the test split (sanity that ground truth is
        genuine, not that the matcher is perfect)."""
        from src.services.anomaly_detection.duplicate_detection import (
            evaluate_duplicate_detection,
            select_similarity_threshold,
        )
        dataset = syn.generate_synthetic_dataset(
            syn.ExperimentConfig(
                seed=2026, employee_count=1000,
                anomaly_rate=0.10, rare_legitimate_rate=0.04,
            )
        )
        threshold = select_similarity_threshold(dataset)
        evaluation = evaluate_duplicate_detection(dataset, "similarity", threshold=threshold)
        if evaluation.true_pair_count == 0:
            self.skipTest("no true duplicate pairs in test split for this seed")
        self.assertGreater(
            evaluation.metrics.true_positives, 0,
            "with genuine same-person ground truth the similarity matcher should "
            "recover at least one true pair",
        )


class R6CandidateCountConservationTests(unittest.TestCase):
    """R6: candidate-set confusion counts must not exceed the candidate universe."""

    def test_one_missed_pair_in_one_candidate_universe_conserves_counts(self):
        metrics = confusion_counts_for_pairs(set(), {("A", "B")}, 1)
        total = (
            metrics.true_positives
            + metrics.false_positives
            + metrics.true_negatives
            + metrics.false_negatives
        )
        self.assertEqual(total, 1, f"counts {metrics} exceed the 1-pair universe")
        self.assertEqual(metrics.false_negatives, 1)
        self.assertEqual(metrics.true_negatives, 0)

    def test_counts_conserve_across_mixed_candidate_universe(self):
        # Universe of 4 candidate pairs. 2 true (AB, CD). Predict AB (TP) and EF
        # (FP, but EF is outside the universe -> should not inflate counts beyond 4).
        predicted = {("A", "B"), ("C", "D")}
        true_pairs = {("A", "B"), ("E", "F")}
        metrics = confusion_counts_for_pairs(predicted, true_pairs, 4)
        total = (
            metrics.true_positives
            + metrics.false_positives
            + metrics.true_negatives
            + metrics.false_negatives
        )
        self.assertLessEqual(total, 4, f"counts {metrics} exceed the 4-pair universe")

    def test_no_predictions_no_truth_all_true_negative(self):
        metrics = confusion_counts_for_pairs(set(), set(), 5)
        self.assertEqual(metrics.true_positives, 0)
        self.assertEqual(metrics.false_positives, 0)
        self.assertEqual(metrics.false_negatives, 0)
        self.assertEqual(metrics.true_negatives, 5)

    def test_perfect_prediction_conserves(self):
        pairs = {("A", "B"), ("C", "D")}
        metrics = confusion_counts_for_pairs(pairs, pairs, 3)
        total = (
            metrics.true_positives
            + metrics.false_positives
            + metrics.true_negatives
            + metrics.false_negatives
        )
        self.assertEqual(total, 3)
        self.assertEqual(metrics.true_positives, 2)
        self.assertEqual(metrics.true_negatives, 1)


class R2R3R4GeneratorIntegrityTests(unittest.TestCase):
    """R2/R3/R4: rare-legitimate histories must be internally consistent.

    R2 — policy_transition rare cases must NOT contain invariant contradictions
         (no promotion before hire, no same-day double promotion, service met).
    R3 — every rare-legitimate case must have a realized causal intervention
         (non-empty causal_events) that matches its claimed mechanism.
    R4 — current_level must equal the last effective (non-superseded) promotion's
         resulting level, not a hardcoded 'L6'.
    """

    @classmethod
    def setUpClass(cls):
        from src.research.independent_scenarios import (
            independent_scenario_matrix,
            generate_independent_world,
        )
        cls.worlds = [
            generate_independent_world(spec)
            for spec in independent_scenario_matrix(360)
        ]

    # --- R3: every rare case has a realized intervention ---
    def test_every_rare_legitimate_case_has_causal_events(self):
        from src.research.independent_scenarios import TruthCategory
        empty = []
        for world in self.worlds:
            for truth in world.truth:
                if truth.category is TruthCategory.RARE_LEGITIMATE and not truth.causal_events:
                    empty.append((world.spec.scenario_id, truth.employee_id, truth.realized_mechanism))
        self.assertEqual(empty, [], f"{len(empty)} rare-legitimate cases have no causal event: {empty[:5]}")

    # --- R2: transition rare cases have no invariant contradictions ---
    def test_policy_transition_rare_cases_have_no_invariant_contradictions(self):
        from src.research.independent_scenarios import TruthCategory
        from src.research.independent_scenario_adapter import adapt_independent_world
        from src.services.anomaly_detection.deterministic_checks import validate_invariant_record
        offenders = []
        for world in self.worlds:
            if world.spec.rare_pattern != "policy_transition":
                continue
            scenario = adapt_independent_world(world)
            rare_ids = {
                t.employee_id for t in world.truth
                if t.category is TruthCategory.RARE_LEGITIMATE
            }
            for record in scenario.dataset.records:
                if record.identity.employee_id in rare_ids:
                    findings = validate_invariant_record(record)
                    if findings:
                        offenders.append((world.spec.scenario_id, record.identity.employee_id, [f.code for f in findings]))
        self.assertEqual(offenders, [], f"{len(offenders)} policy_transition rare cases have invariant contradictions: {offenders[:5]}")

    def test_policy_transition_promotions_not_before_hire(self):
        from src.research.independent_scenarios import TruthCategory, IndependentEventKind
        offenders = []
        for world in self.worlds:
            if world.spec.rare_pattern != "policy_transition":
                continue
            rare_ids = {
                t.employee_id for t in world.truth
                if t.category is TruthCategory.RARE_LEGITIMATE
            }
            for emp in world.employees:
                if emp.employee_id not in rare_ids:
                    continue
                for ev in emp.events:
                    if ev.kind is IndependentEventKind.PROMOTION and ev.effective_date < emp.hire_date:
                        offenders.append((world.spec.scenario_id, emp.employee_id, str(ev.effective_date), str(emp.hire_date)))
        self.assertEqual(offenders, [], f"{len(offenders)} transition promotions before hire: {offenders[:5]}")

    def test_no_same_day_double_promotion_in_rare_cases(self):
        from src.research.independent_scenarios import TruthCategory, IndependentEventKind
        offenders = []
        for world in self.worlds:
            rare_ids = {
                t.employee_id for t in world.truth
                if t.category is TruthCategory.RARE_LEGITIMATE
            }
            for emp in world.employees:
                if emp.employee_id not in rare_ids:
                    continue
                promo_dates = [
                    ev.effective_date for ev in emp.events
                    if ev.kind is IndependentEventKind.PROMOTION
                ]
                if len(promo_dates) != len(set(promo_dates)):
                    offenders.append((world.spec.scenario_id, emp.employee_id, [str(d) for d in promo_dates]))
        self.assertEqual(offenders, [], f"{len(offenders)} rare cases with same-day double promotion: {offenders[:5]}")

    # --- R4: current_level consistent with last effective promotion ---
    def test_current_level_matches_last_effective_promotion(self):
        from src.research.independent_scenarios import IndependentEventKind
        offenders = []
        for world in self.worlds:
            for emp in world.employees:
                superseded = {
                    e.correction_of_event_id for e in emp.events
                    if e.correction_of_event_id
                }
                promotions = [
                    e for e in emp.events
                    if e.kind is IndependentEventKind.PROMOTION
                    and e.event_id not in superseded
                ]
                if not promotions:
                    continue
                last = max(promotions, key=lambda e: (e.effective_date, e.event_id))
                if emp.current_level != last.level_after:
                    offenders.append((world.spec.scenario_id, emp.employee_id, emp.current_level, last.level_after))
        self.assertEqual(offenders, [], f"{len(offenders)} histories with current_level != last promotion level: {offenders[:5]}")


if __name__ == "__main__":
    unittest.main()
