import os
import tempfile
import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import src.database.connection as db
from src.database.models import (
    Base,
    AuditLog,
    Commendation,
    CommendationEmployee,
    Employee,
    PerformanceScore,
    PromotionHistory,
    SalaryIncrementHistory,
    Sanction,
    SystemUser,
)


class IsolatedDatabaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._old_engine = db.engine
        cls._old_session_local = db.SessionLocal
        cls._tmp = tempfile.NamedTemporaryFile(prefix="myhr_test_", suffix=".db", delete=False)
        cls._tmp.close()
        cls.engine = create_engine(f"sqlite:///{cls._tmp.name}", echo=False)
        db.engine = cls.engine
        db.SessionLocal = sessionmaker(bind=cls.engine)
        Base.metadata.create_all(cls.engine)
        with db.SessionLocal() as session:
            db._seed_defaults(session)

    @classmethod
    def tearDownClass(cls):
        db.SessionLocal = cls._old_session_local
        db.engine = cls._old_engine
        cls.engine.dispose()
        try:
            os.remove(cls._tmp.name)
        except OSError:
            pass

    def setUp(self):
        self.session = db.SessionLocal()
        self.admin = self.session.query(SystemUser).filter_by(username="admin").one()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def title(self, name):
        return self.session.query(db.Title).filter_by(name=name).one()

    def make_employee(self, *, title_name="L7", degree="BSc", join_months_ago=0, salary=2400, status="active"):
        title = self.title(title_name)
        suffix = self.session.query(Employee).count() + 1
        employee = Employee(
            employee_id=f"EMP-T{suffix:04d}",
            first_name=f"Test{suffix}",
            last_name="Employee",
            degree=degree,
            work_email=f"test{suffix}@example.test",
            position="Analyst",
            join_date=db._add_months(datetime.utcnow(), -join_months_ago),
            base_salary=salary,
            status=status,
            title=title,
        )
        self.session.add(employee)
        self.session.flush()
        return employee

    def add_commendation(self, employee, months_impact=-3, issued_months_ago=1):
        commendation = Commendation(
            commendation_ref=db.generate_commendation_ref(self.session),
            title="Regression commendation",
            description="Test commendation",
            category=2,
            months_impact=months_impact,
            issued_by_id=self.admin.id,
            issued_at=db._add_months(datetime.utcnow(), -issued_months_ago),
        )
        self.session.add(commendation)
        self.session.flush()
        self.session.add(CommendationEmployee(commendation_id=commendation.id, employee_id=employee.id))
        self.session.flush()
        return commendation

    def add_sanction(self, employee, delay_months=2, issued_months_ago=1, resolved=False):
        sanction = Sanction(
            sanction_ref=db.generate_sanction_ref(self.session),
            employee_id=employee.id,
            sanction_type="written_warning",
            reason="Regression sanction",
            delay_months=delay_months,
            issued_by_id=self.admin.id,
            issued_at=db._add_months(datetime.utcnow(), -issued_months_ago),
            is_resolved=resolved,
            resolved_at=datetime.utcnow() if resolved else None,
        )
        self.session.add(sanction)
        self.session.flush()
        return sanction


class PromotionRaceTests(IsolatedDatabaseTestCase):
    def test_promotion_math_uses_commendations_and_only_active_sanctions(self):
        employee = self.make_employee(join_months_ago=30)
        self.add_commendation(employee, months_impact=-3)
        self.add_sanction(employee, delay_months=2, resolved=False)
        self.add_sanction(employee, delay_months=5, resolved=True)

        race = db.calculate_months_remaining(employee, self.session)

        self.assertEqual(race["base_months"], 36)
        self.assertEqual(race["months_elapsed"], 30)
        self.assertEqual(race["commendation_reduction"], 3)
        self.assertEqual(race["sanction_addition"], 2)
        self.assertEqual(race["months_remaining"], 5)
        self.assertFalse(race["eligible"])

    def test_batch_promotion_math_matches_single_employee_math(self):
        standard = self.make_employee(join_months_ago=35)
        self.add_commendation(standard, months_impact=-1)
        self.add_sanction(standard, delay_months=2)
        other = self.make_employee(title_name="Other", degree="Other", join_months_ago=14, salary=2200)

        batch = db.calculate_months_remaining_batch([standard, other], self.session)
        single = db.calculate_months_remaining(standard, self.session)

        for key in ("months_remaining", "base_months", "months_elapsed", "commendation_reduction", "sanction_addition", "eligible"):
            self.assertEqual(batch[standard.id][key], single[key])
        self.assertFalse(batch[other.id]["has_next_level"])
        self.assertIsNone(batch[other.id]["months_remaining"])
        self.assertEqual(batch[other.id]["progress_pct"], 0)

    def test_commendation_limit_resets_after_promotion(self):
        employee = self.make_employee(join_months_ago=48)
        old_title = self.title("L7")
        new_title = self.title("L6")
        for month in (40, 39, 38):
            self.add_commendation(employee, months_impact=-1, issued_months_ago=month)
        promotion = PromotionHistory(
            employee_id=employee.id,
            from_title_id=old_title.id,
            to_title_id=new_title.id,
            approved_by_id=self.admin.id,
            basis="time_based",
            months_taken=36,
            promoted_at=db._add_months(datetime.utcnow(), -12),
        )
        employee.title = new_title
        self.session.add(promotion)
        self.add_commendation(employee, months_impact=-1, issued_months_ago=2)
        self.session.flush()

        self.assertEqual(db.count_commendations_in_current_role(employee, self.session), 1)
        self.assertTrue(db.can_receive_commendation(employee, self.session))

    def test_batch_commendation_count_matches_single_employee_count(self):
        employee = self.make_employee(join_months_ago=48)
        old_title = self.title("L7")
        new_title = self.title("L6")
        for month in (40, 39, 38):
            self.add_commendation(employee, months_impact=-1, issued_months_ago=month)
        promotion = PromotionHistory(
            employee_id=employee.id,
            from_title_id=old_title.id,
            to_title_id=new_title.id,
            approved_by_id=self.admin.id,
            basis="time_based",
            months_taken=36,
            promoted_at=db._add_months(datetime.utcnow(), -12),
        )
        employee.title = new_title
        self.session.add(promotion)
        self.add_commendation(employee, months_impact=-1, issued_months_ago=2)
        self.session.flush()

        batch = db.count_commendations_in_current_role_batch([employee], self.session)

        self.assertEqual(batch[employee.id], db.count_commendations_in_current_role(employee, self.session))

    def test_other_employee_has_only_sub_race_and_no_main_promotion_race(self):
        employee = self.make_employee(title_name="Other", degree="Other", join_months_ago=26, salary=2200)

        race = db.calculate_months_remaining(employee, self.session)
        sub_race = db.calculate_sub_race(employee, self.session)

        self.assertFalse(race["has_next_level"])
        self.assertFalse(race["eligible"])
        self.assertTrue(sub_race["is_other_track"])
        self.assertIsNone(sub_race["expected_promotion_date"])
        self.assertGreaterEqual(len(sub_race["steps"]), 3)
        self.assertEqual(sub_race["steps"][0]["label"], "Other.1")

    def test_promotion_decision_evidence_clear_when_performance_supports_approval(self):
        employee = self.make_employee(join_months_ago=40)
        db.record_performance_score(
            employee.id,
            self.admin.id,
            85,
            self.session,
            review_type="promotion",
            review_period="2026",
        )

        evidence = db.get_promotion_decision_evidence(employee.id, self.session)

        self.assertTrue(evidence["success"])
        self.assertTrue(evidence["race_eligible"])
        self.assertEqual(evidence["latest_score"], "85/100")
        self.assertEqual(evidence["performance_band"], "Exceeds Expectations")
        self.assertEqual(evidence["active_sanctions"], 0)
        self.assertEqual(evidence["recommendation"], "clear")
        self.assertIn("supports the promotion decision", evidence["strengths"][0])

    def test_promotion_decision_evidence_flags_bad_performance_and_active_sanctions(self):
        employee = self.make_employee(join_months_ago=50)
        self.add_sanction(employee, delay_months=2, resolved=False)
        db.record_performance_score(
            employee.id,
            self.admin.id,
            55,
            self.session,
            review_type="promotion",
            review_period="2026",
        )

        evidence = db.get_promotion_decision_evidence(employee.id, self.session)

        self.assertTrue(evidence["success"])
        self.assertTrue(evidence["race_eligible"])
        self.assertEqual(evidence["performance_band"], "Unsatisfactory")
        self.assertEqual(evidence["active_sanctions"], 1)
        self.assertEqual(evidence["active_sanction_delay_months"], 2)
        self.assertEqual(evidence["recommendation"], "risk_flagged")
        self.assertTrue(any("below the acceptable" in warning for warning in evidence["warnings"]))
        self.assertTrue(any("active sanction" in warning for warning in evidence["warnings"]))


class SalaryIncrementAndAuditTests(IsolatedDatabaseTestCase):
    def test_increment_due_and_apply_records_history_and_audit_snapshot(self):
        employee = self.make_employee(join_months_ago=13, salary=2000)

        due_ids = {emp.id for emp in db.get_increment_due_employees(self.session)}
        self.assertIn(employee.id, due_ids)

        result = db.apply_salary_increment(employee.id, self.admin.id, self.session, notes="Regression approval")
        self.assertTrue(result["success"])
        self.assertEqual(result["salary_before"], 2000)
        self.assertEqual(result["salary_after"], 2060)

        refreshed = self.session.query(Employee).filter_by(id=employee.id).one()
        self.assertEqual(refreshed.base_salary, 2060)
        self.assertNotIn(refreshed.id, {emp.id for emp in db.get_increment_due_employees(self.session)})

        history = self.session.query(SalaryIncrementHistory).filter_by(employee_id=employee.id).one()
        self.assertEqual(history.salary_before, 2000)
        self.assertEqual(history.salary_after, 2060)
        self.assertIn("Sub-race milestone", history.notes)

        audit = self.session.query(AuditLog).filter_by(action="salary_increment.apply", target_id=employee.id).one()
        self.assertEqual(audit.performed_by_username, "admin")
        self.assertEqual(audit.performed_by_name, "System Administrator")

    def test_login_rejects_soft_deleted_hr_and_audit_keeps_name_snapshot(self):
        hr = self.session.query(SystemUser).filter_by(username="hr_officer").one()
        db.log_action(
            self.session,
            action="sanction.issue",
            performed_by_id=hr.id,
            target_table="employee",
            target_id=123,
            description="Snapshot test",
        )
        self.session.commit()

        audit = self.session.query(AuditLog).filter_by(action="sanction.issue").one()
        self.assertEqual(audit.performed_by_username, "hr_officer")
        self.assertEqual(audit.performed_by_name, "HR Officer")

        hr.username = "hr_archived"
        hr.full_name = "Archived HR"
        hr.is_active = False
        self.session.commit()

        self.assertIsNone(db.verify_login("hr_archived", "hr123"))
        unchanged_audit = self.session.query(AuditLog).filter_by(id=audit.id).one()
        self.assertEqual(unchanged_audit.performed_by_username, "hr_officer")
        self.assertEqual(unchanged_audit.performed_by_name, "HR Officer")


class PerformanceScoreTests(IsolatedDatabaseTestCase):
    def test_record_performance_score_creates_history_and_audit(self):
        employee = self.make_employee(join_months_ago=18)

        result = db.record_performance_score(
            employee.id,
            self.admin.id,
            82,
            self.session,
            review_type="annual",
            review_period="2026",
            notes="Annual review",
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["percentage"], 82)
        record = self.session.query(PerformanceScore).filter_by(employee_id=employee.id).one()
        self.assertEqual(record.score, 82)
        self.assertEqual(record.max_score, 100)
        self.assertEqual(record.percentage, 82)
        self.assertEqual(record.review_type, "annual")
        self.assertEqual(record.review_period, "2026")
        self.assertEqual(record.notes, "Annual review")

        latest = db.get_latest_performance_score(employee.id, self.session)
        self.assertEqual(latest.id, record.id)

        audit = self.session.query(AuditLog).filter_by(
            action="performance_review.record",
            target_id=record.id,
        ).one()
        self.assertEqual(audit.target_table, "performance_score")
        self.assertEqual(audit.target_id, record.id)
        self.assertIn("82", audit.description)
        self.assertEqual(audit.performed_by_username, "admin")
        self.assertEqual(db.performance_score_band(record.score, record.max_score), "Exceeds Expectations")

    def test_record_performance_score_rejects_out_of_range_values(self):
        employee = self.make_employee(join_months_ago=18)

        result = db.record_performance_score(employee.id, self.admin.id, 120, self.session, max_score=100)

        self.assertFalse(result["success"])
        self.assertEqual(self.session.query(PerformanceScore).filter_by(employee_id=employee.id).count(), 0)

    def test_record_performance_score_rejects_duplicate_review_period(self):
        employee = self.make_employee(join_months_ago=18)
        first = db.record_performance_score(
            employee.id,
            self.admin.id,
            75,
            self.session,
            review_type="annual",
            review_period="2026",
        )
        second = db.record_performance_score(
            employee.id,
            self.admin.id,
            81,
            self.session,
            review_type="annual",
            review_period="2026",
        )

        self.assertTrue(first["success"])
        self.assertFalse(second["success"])
        self.assertIn("already exists", second["error"])
        self.assertEqual(self.session.query(PerformanceScore).filter_by(employee_id=employee.id).count(), 1)

    def test_performance_rubric_calculates_weighted_score(self):
        employee = self.make_employee(join_months_ago=18)

        result = db.record_performance_score(
            employee.id,
            self.admin.id,
            0,
            self.session,
            review_type="promotion",
            review_period="2026",
            goal_score=90,
            competency_score=80,
            conduct_score=70,
            teamwork_score=60,
        )

        self.assertTrue(result["success"])
        record = self.session.query(PerformanceScore).filter_by(employee_id=employee.id).one()
        self.assertEqual(record.score, 80)
        self.assertEqual(record.goal_score, 90)
        self.assertEqual(record.competency_score, 80)
        self.assertEqual(record.conduct_score, 70)
        self.assertEqual(record.teamwork_score, 60)
        self.assertEqual(db.performance_score_band(record.score, record.max_score), "Exceeds Expectations")

    def test_update_performance_score_recalculates_and_audits(self):
        employee = self.make_employee(join_months_ago=18)
        created = db.record_performance_score(
            employee.id,
            self.admin.id,
            75,
            self.session,
            review_type="annual",
            review_period="2026",
        )
        record = self.session.get(PerformanceScore, created["record_id"])

        result = db.update_performance_score(
            record.id,
            self.admin.id,
            self.session,
            score=0,
            review_type="annual",
            review_period="2026",
            goal_score=100,
            competency_score=90,
            conduct_score=80,
            teamwork_score=70,
            notes="Corrected after manager review",
        )

        self.assertTrue(result["success"])
        self.session.refresh(record)
        self.assertEqual(record.score, 90)
        self.assertEqual(record.goal_score, 100)
        self.assertEqual(record.competency_score, 90)
        self.assertEqual(record.conduct_score, 80)
        self.assertEqual(record.teamwork_score, 70)
        self.assertEqual(record.notes, "Corrected after manager review")
        audit = self.session.query(AuditLog).filter_by(
            action="performance_review.update",
            target_id=record.id,
        ).one()
        self.assertIn("Performance review updated", audit.description)
        self.assertIsNotNone(audit.before_value)
        self.assertIsNotNone(audit.after_value)

    def test_update_performance_score_rejects_duplicate_period(self):
        employee = self.make_employee(join_months_ago=18)
        first = db.record_performance_score(
            employee.id,
            self.admin.id,
            80,
            self.session,
            review_type="annual",
            review_period="2026",
        )
        second = db.record_performance_score(
            employee.id,
            self.admin.id,
            82,
            self.session,
            review_type="annual",
            review_period="2025",
        )

        result = db.update_performance_score(
            second["record_id"],
            self.admin.id,
            self.session,
            score=85,
            review_type="annual",
            review_period="2026",
        )

        self.assertFalse(result["success"])
        self.assertIn("already exists", result["error"])
        original = self.session.get(PerformanceScore, first["record_id"])
        unchanged = self.session.get(PerformanceScore, second["record_id"])
        self.assertEqual(original.review_period, "2026")
        self.assertEqual(unchanged.review_period, "2025")


class ValidationTests(IsolatedDatabaseTestCase):
    def test_salary_range_validation_uses_configured_title_limits(self):
        title = self.title("L7")

        valid, message = db.validate_salary_for_title(title, 2400)
        self.assertTrue(valid)
        self.assertEqual(message, "")

        valid, message = db.validate_salary_for_title(title, 1999)
        self.assertFalse(valid)
        self.assertIn("2,000", message)
        self.assertIn("2,800", message)

    def test_other_org_unit_is_single_branch_under_organization(self):
        organization = db.OrgUnit(name="NexaSoft", unit_type="organization")
        self.session.add(organization)
        self.session.flush()

        first = db.ensure_others_org_unit(self.session)
        second = db.ensure_others_org_unit(self.session)

        self.assertEqual(first.id, second.id)
        self.assertEqual(first.name, "OTHERS")
        self.assertEqual(first.unit_type, "division")
        self.assertEqual(first.parent_id, organization.id)


if __name__ == "__main__":
    unittest.main()
