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
from datetime import date
from unittest.mock import patch

import src.services.anomaly_detection.synthetic_data as syn
from src.services.anomaly_detection.duplicate_detection import (
    confusion_counts_for_pairs,
    evaluate_duplicate_detection,
    select_similarity_threshold,
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

    def test_duplicate_variant_shares_source_employment_history(self):
        dataset, _ = self._generate_with_latent_capture()
        by_id = {record.identity.employee_id: record for record in dataset.records}
        duplicates = [
            record for record in dataset.records
            if record.duplicate_of_employee_id is not None
        ]
        self.assertTrue(duplicates)
        for duplicate in duplicates:
            source = by_id[duplicate.duplicate_of_employee_id]
            self.assertEqual(duplicate.hire_date, source.hire_date)
            self.assertEqual(duplicate.department, source.department)
            self.assertEqual(duplicate.role, source.role)
            self.assertEqual(duplicate.employment_track, source.employment_track)
            self.assertEqual(duplicate.current_level, source.current_level)
            self.assertEqual(duplicate.events, source.events)

    def test_duplicate_clusters_have_plausible_hire_age(self):
        dataset, _ = self._generate_with_latent_capture()
        cluster_records = [
            record for record in dataset.records
            if record.latent_person_id is not None
        ]
        self.assertTrue(cluster_records)
        for record in cluster_records:
            age_at_hire = (
                record.hire_date - record.identity.date_of_birth
            ).days / 365.2425
            self.assertGreaterEqual(age_at_hire, 18.0)


class R6CandidateCountConservationTests(unittest.TestCase):
    """R6: candidate-set confusion counts must not exceed the candidate universe."""

    def test_one_missed_pair_in_one_candidate_universe_conserves_counts(self):
        universe = {("A", "B")}
        metrics = confusion_counts_for_pairs(set(), {("A", "B")}, universe)
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
        universe = {
            ("A", "B"), ("C", "D"), ("E", "F"), ("G", "H"),
        }
        predicted = {("A", "B"), ("C", "D")}
        true_pairs = {("A", "B"), ("E", "F")}
        metrics = confusion_counts_for_pairs(predicted, true_pairs, universe)
        total = (
            metrics.true_positives
            + metrics.false_positives
            + metrics.true_negatives
            + metrics.false_negatives
        )
        self.assertEqual(total, 4)
        self.assertEqual(metrics.true_positives, 1)
        self.assertEqual(metrics.false_positives, 1)
        self.assertEqual(metrics.false_negatives, 1)
        self.assertEqual(metrics.true_negatives, 1)
        self.assertAlmostEqual(metrics.precision, 0.5)
        self.assertAlmostEqual(metrics.recall, 0.5)
        self.assertAlmostEqual(metrics.false_positive_rate, 0.5)

    def test_prediction_outside_universe_is_rejected(self):
        with self.assertRaises(ValueError):
            confusion_counts_for_pairs(
                {("A", "B")},
                {("A", "B")},
                {("C", "D")},
            )

    def test_truth_outside_universe_is_a_blocking_miss_not_candidate_fn(self):
        universe = {("A", "B"), ("C", "D")}
        metrics = confusion_counts_for_pairs(
            set(),
            {("X", "Y")},
            universe,
        )
        self.assertEqual(metrics.false_negatives, 0)
        self.assertEqual(metrics.true_negatives, 2)

    def test_no_predictions_no_truth_all_true_negative(self):
        universe = {(str(index), str(index + 1)) for index in range(5)}
        metrics = confusion_counts_for_pairs(set(), set(), universe)
        self.assertEqual(metrics.true_positives, 0)
        self.assertEqual(metrics.false_positives, 0)
        self.assertEqual(metrics.false_negatives, 0)
        self.assertEqual(metrics.true_negatives, 5)

    def test_perfect_prediction_conserves(self):
        pairs = {("A", "B"), ("C", "D")}
        universe = pairs | {("E", "F")}
        metrics = confusion_counts_for_pairs(pairs, pairs, universe)
        total = (
            metrics.true_positives
            + metrics.false_positives
            + metrics.true_negatives
            + metrics.false_negatives
        )
        self.assertEqual(total, 3)
        self.assertEqual(metrics.true_positives, 2)
        self.assertEqual(metrics.true_negatives, 1)

    @staticmethod
    def _record(
        employee_id: str,
        name: str,
        dob: date,
        national_id: str,
        email: str,
        *,
        duplicate_of: str | None = None,
        split: syn.DatasetSplit = syn.DatasetSplit.TEST,
    ) -> syn.WorkforceHistoryRecord:
        return syn.WorkforceHistoryRecord(
            identity=syn.EmployeeIdentity(
                employee_id, name, dob, national_id, email
            ),
            split=split,
            employment_track=syn.EmploymentTrack.OTHER,
            current_level=None,
            department="D",
            role="R",
            hire_date=date(2020, 1, 1),
            events=(),
            duplicate_of_employee_id=duplicate_of,
        )

    @staticmethod
    def _dataset(*records: syn.WorkforceHistoryRecord) -> syn.SyntheticDataset:
        return syn.SyntheticDataset(
            records=tuple(records),
            metadata=syn.SyntheticDatasetMetadata(
                schema_version="test",
                run_id="r6-explicit-universe",
                seed=1,
                employee_count=len(records),
                split_counts={"test": len(records)},
                label_counts={},
            ),
        )

    def test_exact_pair_outside_similarity_block_uses_full_pair_universe(self):
        left = self._record(
            "A", "Alice North", date(1990, 1, 1), "ID-A", "shared@example.test"
        )
        right = self._record(
            "B", "Boris South", date(1991, 2, 2), "ID-B", "shared@example.test",
            duplicate_of="A",
        )
        evaluation = evaluate_duplicate_detection(self._dataset(left, right), "exact")
        self.assertEqual(evaluation.blocked_pair_count, 0)
        self.assertEqual(evaluation.candidate_pair_count, 1)
        self.assertEqual(evaluation.candidate_metrics.true_positives, 1)
        self.assertEqual(evaluation.metrics.true_positives, 1)

    def test_similarity_candidate_counts_partition_the_blocked_universe(self):
        dataset = syn.generate_synthetic_dataset(
            syn.ExperimentConfig(seed=2026, employee_count=200)
        )
        evaluation = evaluate_duplicate_detection(dataset, "similarity")
        metrics = evaluation.candidate_metrics
        self.assertEqual(
            evaluation.candidate_pair_count,
            evaluation.blocked_pair_count,
        )
        self.assertEqual(
            metrics.true_positives
            + metrics.false_positives
            + metrics.false_negatives
            + metrics.true_negatives,
            evaluation.candidate_pair_count,
        )

    def test_unblocked_truth_reduces_blocking_recall_not_candidate_f1(self):
        # A/B are a true pair with no shared blocking key. C/D provide one
        # non-duplicate blocked pair so threshold selection remains defined.
        records = (
            self._record(
                "A", "Alice North", date(1990, 1, 1), "ID-A", "a@example.test",
                split=syn.DatasetSplit.VALIDATION,
            ),
            self._record(
                "B", "Boris South", date(1991, 2, 2), "ID-B", "b@example.test",
                duplicate_of="A", split=syn.DatasetSplit.VALIDATION,
            ),
            self._record(
                "C", "Chris One", date(1985, 3, 3), "ID-C", "c@example.test",
                split=syn.DatasetSplit.VALIDATION,
            ),
            self._record(
                "D", "Chris Two", date(1986, 4, 4), "ID-D", "d@example.test",
                split=syn.DatasetSplit.VALIDATION,
            ),
        )
        dataset = self._dataset(*records)
        threshold = select_similarity_threshold(
            dataset, split=syn.DatasetSplit.VALIDATION
        )
        evaluation = evaluate_duplicate_detection(
            dataset,
            "similarity",
            threshold=threshold,
            split=syn.DatasetSplit.VALIDATION,
        )
        self.assertEqual(evaluation.true_pair_count, 1)
        self.assertEqual(evaluation.blocked_true_pair_count, 0)
        self.assertEqual(evaluation.blocking_recall, 0.0)
        self.assertEqual(evaluation.candidate_metrics.false_negatives, 0)

    def test_duplicate_export_includes_candidate_universe_size(self):
        from scripts.run_tdk_research_experiment import _duplicate_rows

        dataset = syn.generate_synthetic_dataset(
            syn.ExperimentConfig(seed=2026, employee_count=200)
        )
        metric_rows, _ = _duplicate_rows(dataset)
        self.assertTrue(metric_rows)
        self.assertTrue(all("candidate_pair_count" in row for row in metric_rows))


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


class R5CorrectionSemanticsTests(unittest.TestCase):
    """R5: corrections must have consistent meaning across rules and features.

    Supersession must apply to ALL fact types (not just promotions), and invalid
    correction graphs (self-links, cycles, dangling targets) must be rejected
    rather than silently hiding events.
    """

    def _record(self, events, observation_date=None):
        return syn.WorkforceHistoryRecord(
            syn.EmployeeIdentity("A", "A", date(1990, 1, 1)),
            syn.DatasetSplit.TEST,
            syn.EmploymentTrack.PROMOTION,
            "L6", "D", "R", date(2020, 1, 1),
            tuple(events),
            observation_date=observation_date,
        )

    def test_corrected_commendation_supersedes_old_credit(self):
        """R5.1: correcting a +6mo commendation to +1mo must yield 1 month, not 7."""
        from src.services.anomaly_detection.policy_history import assess_promotion_history
        from src.services.anomaly_detection.policy_model import PromotionPolicy
        old = syn.AdministrativeEvent(
            syn.AdministrativeEventType.COMMENDATION, date(2021, 1, 1), "C1",
            category=3, recorded_date=date(2021, 1, 1),
        )
        correction = syn.AdministrativeEvent(
            syn.AdministrativeEventType.COMMENDATION, date(2021, 1, 1), "C2",
            category=1, recorded_date=date(2022, 1, 1), correction_of_source_id="C1",
        )
        promo = syn.AdministrativeEvent(
            syn.AdministrativeEventType.PROMOTION, date(2023, 1, 1), "P",
            level_before="L7", level_after="L6",
        )
        assessments = assess_promotion_history(
            self._record([old, correction, promo]), PromotionPolicy()
        )
        self.assertTrue(assessments)
        # Only the corrected commendation (category 1) should contribute; the
        # superseded category-3 commendation must not also be counted.
        policy = PromotionPolicy()
        expected = policy.commendation_credit(1)
        self.assertEqual(assessments[0].commendation_credit_months, expected)

    def test_superseded_invalid_promotion_does_not_remove_corrected_history(self):
        """R5.2: invariant filtering must not flag a superseded invalid promotion."""
        from src.services.anomaly_detection.deterministic_checks import validate_invariant_record
        h = syn.AdministrativeEvent(syn.AdministrativeEventType.HIRE, date(2020, 1, 1), "H")
        old = syn.AdministrativeEvent(
            syn.AdministrativeEventType.PROMOTION, date(2021, 1, 1), "ERR",
            level_before="L7", level_after="L8", recorded_date=date(2021, 1, 1),
        )
        correction = syn.AdministrativeEvent(
            syn.AdministrativeEventType.PROMOTION, date(2023, 1, 1), "COR",
            level_before="L7", level_after="L6", recorded_date=date(2023, 1, 2),
            correction_of_source_id="ERR",
        )
        findings = validate_invariant_record(
            self._record([h, old, correction], date(2024, 1, 1))
        )
        self.assertEqual(findings, ())

    def test_self_correction_does_not_silently_hide_promotion(self):
        """R5.3: a self-referencing correction must not vanish the event silently."""
        from src.services.anomaly_detection.policy_history import assess_promotion_history
        from src.services.anomaly_detection.policy_model import PromotionPolicy
        promo = syn.AdministrativeEvent(
            syn.AdministrativeEventType.PROMOTION, date(2020, 2, 1), "P",
            level_before="L7", level_after="L6", correction_of_source_id="P",
        )
        # Either raise (reject invalid graph) or keep the promotion; must NOT
        # silently erase it.
        try:
            assessments = assess_promotion_history(self._record([promo]), PromotionPolicy())
        except ValueError:
            return  # rejecting the invalid self-link is acceptable
        self.assertTrue(
            assessments,
            "self-correction silently erased the promotion instead of being rejected",
        )

    def test_invisible_correction_does_not_supersede_or_raise(self):
        """R5 edge: a correction not yet visible (recorded after the observation
        date) must not supersede its target and must not raise — partial
        visibility is a legitimate bitemporal state, not a malformed graph."""
        from src.services.anomaly_detection.effective_state import effective_events
        old = syn.AdministrativeEvent(
            syn.AdministrativeEventType.PROMOTION, date(2021, 1, 1), "OLD",
            level_before="L7", level_after="L6", recorded_date=date(2021, 1, 1),
        )
        future_correction = syn.AdministrativeEvent(
            syn.AdministrativeEventType.PROMOTION, date(2021, 1, 1), "COR",
            level_before="L7", level_after="L6", recorded_date=date(2027, 1, 1),
            correction_of_source_id="OLD",
        )
        record = self._record([old, future_correction], observation_date=date(2026, 12, 31))
        effective = effective_events(record)
        ids = {e.source_id for e in effective}
        self.assertIn("OLD", ids, "visible original was wrongly superseded by an invisible correction")
        self.assertNotIn("COR", ids, "invisible correction should not be present")

    def test_correction_graph_rejects_self_and_cycle(self):
        """R5: self-links and cycles are always malformed and must raise."""
        from src.services.anomaly_detection.effective_state import (
            superseded_source_ids,
            CorrectionGraphError,
        )
        self_link = syn.AdministrativeEvent(
            syn.AdministrativeEventType.COMMENDATION, date(2021, 1, 1), "X",
            category=1, recorded_date=date(2021, 1, 1), correction_of_source_id="X",
        )
        with self.assertRaises(CorrectionGraphError):
            superseded_source_ids((self_link,))
        a = syn.AdministrativeEvent(
            syn.AdministrativeEventType.COMMENDATION, date(2021, 1, 1), "A",
            category=1, recorded_date=date(2021, 1, 1), correction_of_source_id="B",
        )
        b = syn.AdministrativeEvent(
            syn.AdministrativeEventType.COMMENDATION, date(2021, 1, 2), "B",
            category=1, recorded_date=date(2021, 1, 2), correction_of_source_id="A",
        )
        with self.assertRaises(CorrectionGraphError):
            superseded_source_ids((a, b))

    def test_correction_graph_rejects_duplicate_source_ids(self):
        from src.services.anomaly_detection.effective_state import (
            CorrectionGraphError,
            superseded_source_ids,
        )

        first = syn.AdministrativeEvent(
            syn.AdministrativeEventType.COMMENDATION,
            date(2021, 1, 1),
            "DUP",
        )
        second = syn.AdministrativeEvent(
            syn.AdministrativeEventType.COMMENDATION,
            date(2021, 2, 1),
            "DUP",
        )
        with self.assertRaises(CorrectionGraphError):
            superseded_source_ids((first, second))

    def test_correction_graph_rejects_branching_corrections(self):
        from src.services.anomaly_detection.effective_state import (
            CorrectionGraphError,
            superseded_source_ids,
        )

        original = syn.AdministrativeEvent(
            syn.AdministrativeEventType.SANCTION,
            date(2021, 1, 1),
            "ORIGINAL",
        )
        first = syn.AdministrativeEvent(
            syn.AdministrativeEventType.SANCTION,
            date(2021, 2, 1),
            "COR-1",
            correction_of_source_id="ORIGINAL",
        )
        second = syn.AdministrativeEvent(
            syn.AdministrativeEventType.SANCTION,
            date(2021, 3, 1),
            "COR-2",
            correction_of_source_id="ORIGINAL",
        )
        with self.assertRaises(CorrectionGraphError):
            superseded_source_ids((original, first, second))

    def test_correction_graph_rejects_cross_type_correction(self):
        from src.services.anomaly_detection.effective_state import (
            CorrectionGraphError,
            superseded_source_ids,
        )

        sanction = syn.AdministrativeEvent(
            syn.AdministrativeEventType.SANCTION,
            date(2021, 1, 1),
            "SANCTION",
        )
        commendation = syn.AdministrativeEvent(
            syn.AdministrativeEventType.COMMENDATION,
            date(2021, 2, 1),
            "COMMENDATION",
            correction_of_source_id="SANCTION",
        )
        with self.assertRaises(CorrectionGraphError):
            superseded_source_ids((sanction, commendation))

    def test_superseded_sanction_delay_not_double_counted(self):
        """R5 generalization: correcting a sanction must not keep the old delay."""
        from src.services.anomaly_detection.policy_history import assess_promotion_history
        from src.services.anomaly_detection.policy_model import PromotionPolicy
        hire = syn.AdministrativeEvent(syn.AdministrativeEventType.HIRE, date(2019, 1, 1), "H")
        old_sanction = syn.AdministrativeEvent(
            syn.AdministrativeEventType.SANCTION, date(2021, 6, 1), "S1",
            category=2, recorded_date=date(2021, 6, 1), is_resolved=False,
        )
        # Correction resolves the sanction (no active delay).
        correction = syn.AdministrativeEvent(
            syn.AdministrativeEventType.SANCTION, date(2021, 6, 1), "S2",
            category=2, recorded_date=date(2022, 1, 1), is_resolved=True,
            resolved_date=date(2021, 7, 1), correction_of_source_id="S1",
        )
        promo = syn.AdministrativeEvent(
            syn.AdministrativeEventType.PROMOTION, date(2023, 1, 1), "P",
            level_before="L7", level_after="L6",
        )
        assessments = assess_promotion_history(
            self._record([hire, old_sanction, correction, promo]), PromotionPolicy()
        )
        self.assertTrue(assessments)
        # The superseded unresolved sanction must not contribute an active delay.
        policy = PromotionPolicy()
        resolved_only_delay = assessments[0].sanction_delay_months
        self.assertEqual(
            resolved_only_delay, 0,
            "superseded unresolved sanction still contributed an active delay",
        )


class R8HardNonduplicateCoPartitionTests(unittest.TestCase):
    """R8: a hard-nonduplicate pair must be jointly present in one partition
    (preferably TEST) and the anchor relationship must be recorded, so the
    intended difficult pair is actually evaluated together."""

    def _dataset(self, seed: int = 2026, n: int = 1000):
        return syn.generate_synthetic_dataset(
            syn.ExperimentConfig(
                seed=seed, employee_count=n,
                anomaly_rate=0.10, rare_legitimate_rate=0.04,
            )
        )

    def test_hard_nonduplicate_anchor_is_recorded(self):
        dataset = self._dataset()
        hard = [r for r in dataset.records if r.hard_nonduplicate_kind is not None]
        self.assertGreater(len(hard), 0)
        for r in hard:
            self.assertIsNotNone(
                r.hard_nonduplicate_anchor_id,
                f"hard nonduplicate {r.identity.employee_id} has no recorded anchor",
            )

    def test_hard_nonduplicate_pair_is_co_partitioned(self):
        dataset = self._dataset()
        by_id = {r.identity.employee_id: r for r in dataset.records}
        hard = [r for r in dataset.records if r.hard_nonduplicate_kind is not None]
        for r in hard:
            anchor = by_id.get(r.hard_nonduplicate_anchor_id)
            self.assertIsNotNone(anchor, f"anchor {r.hard_nonduplicate_anchor_id} not found")
            self.assertEqual(
                r.split, anchor.split,
                f"hard pair {r.identity.employee_id}/{anchor.identity.employee_id} "
                f"spans partitions {r.split.value}/{anchor.split.value}",
            )

    def test_hard_nonduplicate_pairs_prefer_test_split(self):
        """At least one hard pair should land in the test split so the evaluated
        partition actually contains difficult negatives."""
        dataset = self._dataset()
        by_id = {r.identity.employee_id: r for r in dataset.records}
        hard = [r for r in dataset.records if r.hard_nonduplicate_kind is not None]
        test_pairs = [
            r for r in hard
            if r.split is syn.DatasetSplit.TEST
            and by_id.get(r.hard_nonduplicate_anchor_id) is not None
            and by_id[r.hard_nonduplicate_anchor_id].split is syn.DatasetSplit.TEST
        ]
        self.assertGreater(
            len(test_pairs), 0,
            "no hard-nonduplicate pair is jointly present in the test split",
        )

    def test_hard_nonduplicates_still_not_true_duplicates(self):
        from src.services.anomaly_detection.duplicate_detection import _true_duplicate_pairs
        dataset = self._dataset()
        records = tuple(r for r in dataset.records if r.split is syn.DatasetSplit.TEST)
        true_pairs = _true_duplicate_pairs(records)
        hard_ids = {r.identity.employee_id for r in dataset.records if r.hard_nonduplicate_kind is not None}
        for left, right in true_pairs:
            self.assertNotIn(left, hard_ids)
            self.assertNotIn(right, hard_ids)

    def test_hard_pairs_co_partitioned_in_fallback_regime(self):
        """When the test split is too small to host all hard pairs, the generator
        must still keep each pair co-partitioned (falling back to a larger split),
        never splitting a pair across partitions."""
        # Small employee count makes the test split too small for 2*4 clean
        # anchors, exercising the VALIDATION/TRAIN fallback host-split path.
        dataset = syn.generate_synthetic_dataset(
            syn.ExperimentConfig(
                seed=2026, employee_count=120,
                anomaly_rate=0.10, rare_legitimate_rate=0.04,
            )
        )
        by_id = {r.identity.employee_id: r for r in dataset.records}
        hard = [r for r in dataset.records if r.hard_nonduplicate_kind is not None]
        for r in hard:
            anchor = by_id.get(r.hard_nonduplicate_anchor_id)
            self.assertIsNotNone(anchor)
            self.assertEqual(
                r.split, anchor.split,
                f"fallback regime split a hard pair across "
                f"{r.split.value}/{anchor.split.value}",
            )


class R10ProvenanceCompletenessTests(unittest.TestCase):
    """R10: source-provenance verification must require the COMPLETE required
    source-path set, not accept an arbitrary non-empty subset."""

    def _metadata(self, revision: str, source_hashes: dict) -> dict:
        return {
            "provenance": {
                "git_dirty": False,
                "git_commit": revision,
                "source_sha256": source_hashes,
            }
        }

    def test_partial_source_hashes_are_rejected(self):
        from scripts.audit_tdk_protocol_artifact import _verify_source_revision, ArtifactAuditError
        from scripts.run_tdk_research_experiment import PROVENANCE_SOURCE_PATHS
        from hashlib import sha256
        import subprocess
        from pathlib import Path
        repo_root = Path(__file__).resolve().parent.parent
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True
        ).stdout.strip()
        # Build a metadata with only ONE of the required source paths hashed.
        one_path = PROVENANCE_SOURCE_PATHS[0]
        content = subprocess.run(
            ["git", "show", f"{revision}:{one_path}"], cwd=repo_root, capture_output=True
        ).stdout
        partial = {one_path: sha256(content).hexdigest()}
        with self.assertRaises(ArtifactAuditError):
            _verify_source_revision(self._metadata(revision, partial), repo_root)

    def test_complete_source_hashes_are_accepted(self):
        from scripts.audit_tdk_protocol_artifact import _verify_source_revision
        from scripts.run_tdk_research_experiment import PROVENANCE_SOURCE_PATHS
        from hashlib import sha256
        import subprocess
        from pathlib import Path
        repo_root = Path(__file__).resolve().parent.parent
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True
        ).stdout.strip()
        complete = {}
        for p in PROVENANCE_SOURCE_PATHS:
            content = subprocess.run(
                ["git", "show", f"{revision}:{p}"], cwd=repo_root, capture_output=True
            ).stdout
            complete[p] = sha256(content).hexdigest()
        # Should not raise.
        _verify_source_revision(self._metadata(revision, complete), repo_root)


class R9MemoryAndExportTests(unittest.TestCase):
    """R9: peak memory must be true high-water allocation; caller tracing must be
    preserved; blocking must not run twice; exports must carry timing+memory."""

    def _dataset(self, seed: int = 2026, n: int = 400):
        return syn.generate_synthetic_dataset(
            syn.ExperimentConfig(
                seed=seed, employee_count=n,
                anomaly_rate=0.10, rare_legitimate_rate=0.04,
            )
        )

    def test_peak_memory_reflects_transient_allocation(self):
        """peak_memory_bytes must be a plausible high-water mark (> a few KB for a
        real evaluation), not a tiny retained-snapshot diff."""
        from src.services.anomaly_detection.duplicate_detection import evaluate_duplicate_detection
        ev = evaluate_duplicate_detection(self._dataset(), "similarity")
        # A real similarity evaluation over 400 records allocates well beyond a
        # few hundred bytes transiently. The old retained-diff metric reported
        # implausibly small values. Require a non-trivial positive peak.
        self.assertGreater(ev.peak_memory_bytes, 1000)

    def test_tracemalloc_state_preserved_when_caller_was_tracing(self):
        """If the caller had tracemalloc running, it must still be running after."""
        import tracemalloc
        from src.services.anomaly_detection.duplicate_detection import evaluate_duplicate_detection
        was_tracing_before = tracemalloc.is_tracing()
        tracemalloc.start()
        try:
            _current_before, peak_before = tracemalloc.get_traced_memory()
            evaluation = evaluate_duplicate_detection(self._dataset(), "exact")
            _current_after, peak_after = tracemalloc.get_traced_memory()
            self.assertTrue(
                tracemalloc.is_tracing(),
                "evaluate_duplicate_detection stopped the caller's tracemalloc",
            )
            self.assertGreaterEqual(peak_after, peak_before)
            self.assertEqual(
                evaluation.peak_memory_bytes,
                0,
                "nested tracing must not claim a call-scoped peak",
            )
        finally:
            tracemalloc.stop()
        # Restore prior state expectation (test started untraced).
        self.assertFalse(was_tracing_before)

    def test_tracemalloc_not_left_running_when_caller_was_not_tracing(self):
        import tracemalloc
        from src.services.anomaly_detection.duplicate_detection import evaluate_duplicate_detection
        self.assertFalse(tracemalloc.is_tracing())
        evaluate_duplicate_detection(self._dataset(), "exact")
        self.assertFalse(
            tracemalloc.is_tracing(),
            "evaluate_duplicate_detection left tracemalloc running",
        )

    def test_export_includes_timing_and_memory_columns(self):
        from scripts.run_tdk_research_experiment import _duplicate_rows
        metric_rows, _ = _duplicate_rows(self._dataset())
        self.assertTrue(metric_rows)
        for row in metric_rows:
            for col in ("blocking_time_s", "scoring_time_s", "peak_memory_bytes"):
                self.assertIn(col, row, f"export missing {col}")


class R7BitemporalEnforcementTests(unittest.TestCase):
    """R7: version identity and effective-time semantics must be enforced."""

    def _record(self, events, observation_date=None):
        return syn.WorkforceHistoryRecord(
            syn.EmployeeIdentity("A", "A", date(1990, 1, 1)),
            syn.DatasetSplit.TEST,
            syn.EmploymentTrack.PROMOTION,
            "L6", "D", "R", date(2019, 1, 1),
            tuple(events),
            observation_date=observation_date,
        )

    def test_unknown_policy_version_is_rejected(self):
        """R7.1: a promotion naming a real policy ID but a nonexistent version
        must be rejected, not silently accepted."""
        from src.services.anomaly_detection.policy_history import (
            assess_promotion_history, PolicyEpoch,
        )
        from src.services.anomaly_detection.policy_model import PromotionPolicy
        hire = syn.AdministrativeEvent(syn.AdministrativeEventType.HIRE, date(2019, 1, 1), "H")
        promo = syn.AdministrativeEvent(
            syn.AdministrativeEventType.PROMOTION, date(2023, 6, 1), "P",
            level_before="L7", level_after="L6", recorded_date=date(2023, 6, 2),
            policy_id="POL", policy_version="not-a-real-version",
        )
        epoch = PolicyEpoch(
            "POL", "1", date(2019, 1, 1), None, date(2019, 1, 1),
            "organization-wide", PromotionPolicy(),
        )
        with self.assertRaises(ValueError):
            assess_promotion_history(self._record([hire, promo]), PromotionPolicy(), (epoch,))

    def test_matching_policy_version_is_accepted(self):
        """R7.1 complement: the correct version must still be accepted."""
        from src.services.anomaly_detection.policy_history import (
            assess_promotion_history, PolicyEpoch,
        )
        from src.services.anomaly_detection.policy_model import PromotionPolicy
        hire = syn.AdministrativeEvent(syn.AdministrativeEventType.HIRE, date(2019, 1, 1), "H")
        promo = syn.AdministrativeEvent(
            syn.AdministrativeEventType.PROMOTION, date(2023, 6, 1), "P",
            level_before="L7", level_after="L6", recorded_date=date(2023, 6, 2),
            policy_id="POL", policy_version="1",
        )
        epoch = PolicyEpoch(
            "POL", "1", date(2019, 1, 1), None, date(2019, 1, 1),
            "organization-wide", PromotionPolicy(),
        )
        assessments = assess_promotion_history(self._record([hire, promo]), PromotionPolicy(), (epoch,))
        self.assertTrue(assessments)

    def test_future_effective_promotion_not_counted_as_completed(self):
        """R7.3: a promotion whose effective date is after the observation date
        must not be counted as a completed promotion, even if already recorded."""
        from src.services.anomaly_detection.features import extract_raw_features
        hire = syn.AdministrativeEvent(syn.AdministrativeEventType.HIRE, date(2019, 1, 1), "H")
        future_promo = syn.AdministrativeEvent(
            syn.AdministrativeEventType.PROMOTION, date(2027, 1, 1), "F",
            level_before="L7", level_after="L6", recorded_date=date(2026, 1, 1),
        )
        record = self._record([hire, future_promo], observation_date=date(2026, 12, 31))
        self.assertEqual(
            extract_raw_features(record).values["promotion_count"], 0.0,
            "a future-effective promotion was counted as completed",
        )

    def test_future_effective_promotion_not_assessed(self):
        """R7.3 complement: policy assessment must also exclude future-effective."""
        from src.services.anomaly_detection.policy_history import assess_promotion_history
        from src.services.anomaly_detection.policy_model import PromotionPolicy
        hire = syn.AdministrativeEvent(syn.AdministrativeEventType.HIRE, date(2019, 1, 1), "H")
        future_promo = syn.AdministrativeEvent(
            syn.AdministrativeEventType.PROMOTION, date(2027, 1, 1), "F",
            level_before="L7", level_after="L6", recorded_date=date(2026, 1, 1),
        )
        record = self._record([hire, future_promo], observation_date=date(2026, 12, 31))
        self.assertEqual(
            len(assess_promotion_history(record, PromotionPolicy())), 0,
            "a future-effective promotion was assessed as completed",
        )


if __name__ == "__main__":
    unittest.main()
