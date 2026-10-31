"""Focused contract tests for paired temporal diagnostics."""

from datetime import date
import unittest

from src.services.anomaly_detection.policy_history import (
    GrandfatheringEvidence,
    PolicyEpoch,
)
from src.services.anomaly_detection.policy_model import PromotionPolicy
from src.services.anomaly_detection.synthetic_data import (
    AdministrativeEvent,
    AdministrativeEventType,
    AnomalyType,
    DatasetSplit,
    EmployeeIdentity,
    EmploymentTrack,
    WorkforceHistoryRecord,
)
from src.services.anomaly_detection.temporal_diagnostics import (
    diagnose_temporal_views,
)


class TemporalDiagnosticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.decision_date = date(2022, 12, 31)
        self.review_date = date(2025, 12, 31)
        self.original = AdministrativeEvent(
            event_type=AdministrativeEventType.PROMOTION,
            event_date=date(2022, 1, 1),
            source_id="PROMOTION-ORIGINAL",
            level_before="L7",
            level_after="L6",
            recorded_date=date(2022, 1, 2),
        )
        self.correction = AdministrativeEvent(
            event_type=AdministrativeEventType.PROMOTION,
            event_date=date(2022, 1, 1),
            source_id="PROMOTION-CORRECTION",
            level_before="L7",
            level_after="L6",
            recorded_date=date(2024, 1, 1),
            recognized_service_months=12,
            correction_of_source_id=self.original.source_id,
        )
        self.future_event = AdministrativeEvent(
            event_type=AdministrativeEventType.PERFORMANCE_REVIEW,
            event_date=date(2023, 1, 1),
            source_id="FUTURE-EFFECTIVE",
            recorded_date=date(2022, 6, 1),
        )
        self.record = WorkforceHistoryRecord(
            identity=EmployeeIdentity(
                employee_id="EMP-001",
                full_name="Example Employee",
                date_of_birth=date(1990, 1, 1),
            ),
            split=DatasetSplit.TEST,
            employment_track=EmploymentTrack.PROMOTION,
            current_level="L6",
            department="Operations",
            role="Analyst",
            hire_date=date(2020, 1, 1),
            events=(self.original, self.correction, self.future_event),
            anomaly_labels=(AnomalyType.CLEAN,),
            observation_date=self.review_date,
        )
        self.policy = PromotionPolicy(service_months_by_level={"L7": 36})

    def test_late_correction_changes_knowledge_not_effective_horizon(self):
        known_then, later_review = diagnose_temporal_views(
            self.record,
            self.policy,
            (),
            (),
            self.decision_date,
            self.review_date,
        )

        self.assertEqual(known_then.view_identifier, "known_then")
        self.assertEqual(later_review.view_identifier, "later_review")
        self.assertEqual(
            known_then.effective_through,
            later_review.effective_through,
        )
        self.assertEqual(known_then.effective_through, self.decision_date)
        self.assertEqual(known_then.recorded_through, self.decision_date)
        self.assertEqual(later_review.recorded_through, self.review_date)

        self.assertIn(self.original.source_id, known_then.visible_event_ids)
        self.assertNotIn(self.correction.source_id, known_then.visible_event_ids)
        self.assertIn(self.original.source_id, later_review.visible_event_ids)
        self.assertIn(self.correction.source_id, later_review.visible_event_ids)
        self.assertNotIn(self.future_event.source_id, known_then.visible_event_ids)
        self.assertNotIn(self.future_event.source_id, later_review.visible_event_ids)

        self.assertEqual(
            known_then.effective_event_ids,
            (self.original.source_id,),
        )
        self.assertEqual(
            later_review.effective_event_ids,
            (self.correction.source_id,),
        )
        self.assertEqual(known_then.promotion_assessment_count, 1)
        self.assertEqual(later_review.promotion_assessment_count, 1)
        self.assertEqual(known_then.total_service_deficit_months, 12)
        self.assertEqual(later_review.total_service_deficit_months, 0)

    def test_counts_match_the_explicit_event_id_collections(self):
        results = diagnose_temporal_views(
            self.record,
            self.policy,
            (),
            (),
            self.decision_date,
            self.review_date,
        )

        self.assertEqual(len(results), 2)
        for result in results:
            with self.subTest(view=result.view_identifier):
                self.assertEqual(
                    result.visible_event_count,
                    len(result.visible_event_ids),
                )
                self.assertEqual(
                    result.effective_event_count,
                    len(result.effective_event_ids),
                )

    def test_entitlement_evidence_is_used_by_both_policy_assessments(self):
        promotion = AdministrativeEvent(
            event_type=AdministrativeEventType.PROMOTION,
            event_date=date(2023, 6, 1),
            source_id="GRANDFATHERED-PROMOTION",
            level_before="L7",
            level_after="L6",
            recorded_date=date(2023, 6, 2),
            policy_id="LEGACY",
            policy_version="1",
        )
        record = WorkforceHistoryRecord(
            identity=self.record.identity,
            split=self.record.split,
            employment_track=self.record.employment_track,
            current_level="L6",
            department=self.record.department,
            role=self.record.role,
            hire_date=date(2020, 1, 1),
            events=(promotion,),
            anomaly_labels=(AnomalyType.CLEAN,),
            observation_date=self.review_date,
        )
        epoch = PolicyEpoch(
            policy_id="LEGACY",
            version="1",
            valid_from=date(2020, 1, 1),
            valid_to=date(2022, 12, 31),
            recorded_at=date(2020, 1, 1),
            jurisdiction="organization-wide",
            policy=PromotionPolicy(service_months_by_level={"L7": 36}),
            grandfather_previous_policy=True,
        )
        evidence = GrandfatheringEvidence(
            employee_id=record.identity.employee_id,
            policy_id=epoch.policy_id,
            policy_version=epoch.version,
            event_source_id=promotion.source_id,
            evidence_reference="ENTITLEMENT-001",
            recorded_at=date(2023, 5, 1),
        )

        results = diagnose_temporal_views(
            record,
            PromotionPolicy(),
            (epoch,),
            (evidence,),
            date(2023, 12, 31),
            self.review_date,
        )

        self.assertEqual(
            [result.promotion_assessment_count for result in results],
            [1, 1],
        )

    def test_review_date_before_decision_date_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "review_date cannot precede decision_date",
        ):
            diagnose_temporal_views(
                self.record,
                self.policy,
                (),
                (),
                self.decision_date,
                date(2021, 12, 31),
            )


if __name__ == "__main__":
    unittest.main()
