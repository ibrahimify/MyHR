"""Semantic regression tests for policy-aware research evaluation contracts."""

from dataclasses import replace
from datetime import date
import unittest

from scripts.run_tdk_independent_development import _record_truth_rows
from src.research.independent_scenario_adapter import adapt_independent_world
from src.research.independent_scenarios import (
    TruthCategory,
    generate_independent_world,
    independent_scenario_matrix,
)
from src.services.anomaly_detection.effective_state import TemporalView, visible_events
from src.services.anomaly_detection.deterministic_checks import validate_invariant_record
from src.services.anomaly_detection.features import FeatureVector
from src.services.anomaly_detection.policy_history import (
    GrandfatheringEvidence,
    PolicyEpoch,
    assess_promotion_history,
)
from src.services.anomaly_detection.policy_model import PromotionPolicy
from src.services.anomaly_detection.protocol_evaluation import (
    _frequency_preserving_policy_permutation,
    _records,
    evaluate_scenario,
    feature_representations,
)
from src.services.anomaly_detection.synthetic_data import (
    AdministrativeEvent,
    AdministrativeEventType,
    AnomalyType,
    DatasetSplit,
    EmployeeIdentity,
    EmploymentTrack,
    WorkforceHistoryRecord,
)


def _record(
    events: tuple[AdministrativeEvent, ...],
    observation_date: date = date(2026, 12, 31),
) -> WorkforceHistoryRecord:
    return WorkforceHistoryRecord(
        identity=EmployeeIdentity("A", "A", date(1990, 1, 1)),
        split=DatasetSplit.TEST,
        employment_track=EmploymentTrack.PROMOTION,
        current_level="L6",
        department="D",
        role="R",
        hire_date=date(2019, 1, 1),
        events=events,
        anomaly_labels=(AnomalyType.CLEAN,),
        observation_date=observation_date,
    )


class EvaluationMembershipTests(unittest.TestCase):
    def test_ambiguous_truth_is_preserved_and_excluded_not_clean(self):
        world = generate_independent_world(
            independent_scenario_matrix(employee_count=120)[0]
        )
        ambiguous = replace(
            world.truth[0],
            category=TruthCategory.AMBIGUOUS_REVIEW_CASE,
        )
        world = replace(world, truth=(ambiguous, *world.truth[1:]))

        scenario = adapt_independent_world(world)
        employee_id = ambiguous.employee_id
        adapted = next(
            record for record in scenario.dataset.records
            if record.identity.employee_id == employee_id
        )
        self.assertEqual(adapted.anomaly_labels, ())
        self.assertFalse(
            scenario.population.evaluation_eligible_by_employee_id[employee_id]
        )
        self.assertEqual(
            scenario.population.evaluation_exclusion_reason_by_employee_id[employee_id],
            "ambiguous_review_case",
        )
        self.assertNotIn(employee_id, {
            record.identity.employee_id
            for record in _records(scenario, adapted.split)
        })

        truth_row = next(
            row for row in _record_truth_rows(world)
            if row["employee_id"] == employee_id
        )
        self.assertEqual(truth_row["truth_category"], "ambiguous_review_case")
        self.assertFalse(truth_row["evaluation_eligible"])
        self.assertEqual(
            truth_row["evaluation_exclusion_reason"],
            "ambiguous_review_case",
        )


class TemporalPolicyTests(unittest.TestCase):
    def test_known_then_and_present_review_have_distinct_visibility(self):
        original = AdministrativeEvent(
            AdministrativeEventType.PROMOTION,
            date(2022, 1, 1),
            "P",
            recorded_date=date(2022, 1, 2),
        )
        late_correction = AdministrativeEvent(
            AdministrativeEventType.PROMOTION,
            date(2022, 1, 1),
            "C",
            recorded_date=date(2025, 1, 1),
            correction_of_source_id="P",
        )
        record = _record((original, late_correction))

        known_then = visible_events(
            record,
            TemporalView.known_then(date(2022, 12, 31)),
        )
        present_review = visible_events(
            record,
            TemporalView.present_review(
                date(2022, 12, 31),
                date(2026, 12, 31),
            ),
        )
        self.assertEqual([event.source_id for event in known_then], ["P"])
        self.assertEqual(
            [event.source_id for event in present_review],
            ["C", "P"],
        )

    def test_policy_knowledge_cutoff_changes_retroactive_view(self):
        promotion = AdministrativeEvent(
            AdministrativeEventType.PROMOTION,
            date(2022, 1, 1),
            "P",
            level_before="L7",
            level_after="L6",
            recorded_date=date(2022, 1, 2),
        )
        old = PolicyEpoch(
            "POL", "1", date(2020, 1, 1), None, date(2020, 1, 1),
            "organization-wide",
            PromotionPolicy(service_months_by_level={"L7": 36}),
        )
        amendment = PolicyEpoch(
            "POL", "2", date(2020, 1, 1), None, date(2025, 1, 1),
            "organization-wide",
            PromotionPolicy(service_months_by_level={"L7": 48}),
        )
        record = _record((promotion,))

        known_then = assess_promotion_history(
            record,
            PromotionPolicy(),
            (old, amendment),
            TemporalView.known_then(date(2022, 12, 31)),
        )
        present_review = assess_promotion_history(
            record,
            PromotionPolicy(),
            (old, amendment),
            TemporalView.present_review(
                date(2022, 12, 31),
                date(2026, 12, 31),
            ),
        )
        self.assertEqual(known_then[0].required_service_months, 36)
        self.assertEqual(present_review[0].required_service_months, 48)

    def test_strict_grandfathering_requires_employee_specific_evidence(self):
        promotion = AdministrativeEvent(
            AdministrativeEventType.PROMOTION,
            date(2023, 6, 1),
            "P",
            level_before="L7",
            level_after="L6",
            recorded_date=date(2023, 6, 2),
            policy_id="LEGACY",
            policy_version="1",
        )
        legacy = PolicyEpoch(
            "LEGACY", "1", date(2020, 1, 1), date(2022, 12, 31),
            date(2020, 1, 1), "organization-wide", PromotionPolicy(),
            grandfather_previous_policy=True,
        )
        record = _record((promotion,))

        with self.assertRaises(ValueError):
            assess_promotion_history(
                record,
                PromotionPolicy(),
                (legacy,),
                grandfathering_evidence=(),
            )
        assessments = assess_promotion_history(
            record,
            PromotionPolicy(),
            (legacy,),
            grandfathering_evidence=(GrandfatheringEvidence(
                employee_id="A",
                policy_id="LEGACY",
                policy_version="1",
                event_source_id="P",
                evidence_reference="GF-A-2023",
                recorded_at=date(2023, 5, 1),
            ),),
        )
        self.assertEqual(len(assessments), 1)

    def test_mismatched_grandfathering_evidence_is_rejected(self):
        promotion = AdministrativeEvent(
            AdministrativeEventType.PROMOTION,
            date(2023, 6, 1),
            "P",
            level_before="L7",
            level_after="L6",
            recorded_date=date(2023, 6, 2),
            policy_id="LEGACY",
            policy_version="1",
        )
        legacy = PolicyEpoch(
            "LEGACY", "1", date(2020, 1, 1), date(2022, 12, 31),
            date(2020, 1, 1), "organization-wide", PromotionPolicy(),
            grandfather_previous_policy=True,
        )

        valid = GrandfatheringEvidence(
            employee_id="A",
            policy_id="LEGACY",
            policy_version="1",
            event_source_id="P",
            evidence_reference="GF-A-P",
            recorded_at=date(2023, 5, 1),
        )
        mismatches = (
            replace(valid, employee_id="OTHER"),
            replace(valid, policy_id="OTHER"),
            replace(valid, policy_version="2"),
            replace(valid, event_source_id="OTHER-PROMOTION"),
            replace(valid, recorded_at=date(2023, 7, 1)),
        )
        for evidence in mismatches:
            with self.subTest(evidence=evidence):
                with self.assertRaisesRegex(ValueError, "not applicable"):
                    assess_promotion_history(
                        _record((promotion,)),
                        PromotionPolicy(),
                        (legacy,),
                        grandfathering_evidence=(evidence,),
                    )

    def test_generated_correction_has_distinct_decision_and_review_states(self):
        spec = next(
            replace(candidate, employee_count=120)
            for candidate in independent_scenario_matrix(employee_count=120)
            if candidate.rare_pattern == "late_correction"
        )
        world = generate_independent_world(spec)
        scenario = adapt_independent_world(world)
        rare_ids = {
            entry.employee_id
            for entry in world.truth
            if entry.category is TruthCategory.RARE_LEGITIMATE
        }
        record = next(
            item for item in scenario.dataset.records
            if item.identity.employee_id in rare_ids
        )
        correction = next(
            event for event in record.events
            if event.correction_of_source_id is not None
        )
        original = next(
            event for event in record.events
            if event.source_id == correction.correction_of_source_id
        )
        # Reconstruct the promotion decision at its intended effective date.
        # The erroneous record was already known, while the formal correction
        # was recorded fourteen days later and is visible only on later review.
        decision_date = correction.event_date

        known_then = visible_events(record, TemporalView.known_then(decision_date))
        later_review = visible_events(
            record,
            TemporalView.present_review(decision_date, date(2026, 12, 31)),
        )

        self.assertIn(original.source_id, {event.source_id for event in known_then})
        self.assertNotIn(correction.source_id, {event.source_id for event in known_then})
        self.assertIn(original.source_id, {event.source_id for event in later_review})
        self.assertIn(correction.source_id, {event.source_id for event in later_review})


class ResidualControlTests(unittest.TestCase):
    def test_policy_shuffle_is_a_frequency_preserving_permutation(self):
        vectors = tuple(
            FeatureVector(
                employee_id=f"E-{index}",
                feature_set="policy_aware",
                values={
                    "event_count": float(index),
                    "policy_service_deficit_months": float(index + 1),
                    "policy_service_deficit_ratio": float(index + 1) / 10,
                    "policy_unexplained_short_promotion": float(index % 2),
                },
            )
            for index in range(6)
        )
        shuffled = _frequency_preserving_policy_permutation(vectors, 1234)
        self.assertEqual(
            shuffled,
            _frequency_preserving_policy_permutation(vectors, 1234),
        )
        columns = (
            "policy_service_deficit_months",
            "policy_service_deficit_ratio",
            "policy_unexplained_short_promotion",
        )
        before = sorted(tuple(vector.values[name] for name in columns) for vector in vectors)
        after = sorted(tuple(vector.values[name] for name in columns) for vector in shuffled)
        self.assertEqual(before, after)
        self.assertEqual(
            [vector.values["event_count"] for vector in vectors],
            [vector.values["event_count"] for vector in shuffled],
        )
        self.assertTrue(any(
            left.values != right.values for left, right in zip(vectors, shuffled)
        ))

    def test_all_predeclared_controls_share_residual_population_and_budget(self):
        world = generate_independent_world(
            independent_scenario_matrix(employee_count=120)[0]
        )
        result = evaluate_scenario(adapt_independent_world(world))
        rows = [
            row for row in result.metric_rows
            if row["method"] == "rule_negative_isolation_forest"
            and row["operating_point"] == "fixed_review_budget"
        ]
        self.assertEqual(
            {row["representation"] for row in rows},
            {item.name for item in feature_representations()},
        )
        self.assertEqual(len({row["evaluation_count"] for row in rows}), 1)
        self.assertEqual(len({row["alert_count"] for row in rows}), 1)

        groups = {}
        for row in result.prediction_rows:
            if (
                row["method"] == "rule_negative_isolation_forest"
                and row["operating_point"] == "fixed_review_budget"
            ):
                groups.setdefault(row["representation"], []).append(row["employee_id"])
        expected_ids = [
            record.identity.employee_id
            for record in _records(adapt_independent_world(world), DatasetSplit.TEST)
            if not validate_invariant_record(record)
        ]
        self.assertTrue(groups)
        for representation, employee_ids in groups.items():
            self.assertEqual(
                employee_ids,
                expected_ids,
                f"residual membership/order differs for {representation}",
            )


if __name__ == "__main__":
    unittest.main()
