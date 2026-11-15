import unittest

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.database import connection as db
from src.database.models import Base, Organization, Title


class TenantReadySchemaTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        db._seed_defaults(self.session)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_default_records_are_scoped_to_seeded_organization(self):
        organization = self.session.get(Organization, db.DEFAULT_ORGANIZATION_ID)
        self.assertIsNotNone(organization)
        self.assertEqual(organization.slug, db.DEFAULT_ORGANIZATION_SLUG)
        self.assertTrue(self.session.query(Title).all())
        self.assertTrue(all(
            title.organization_id == organization.id
            for title in self.session.query(Title).all()
        ))

    def test_title_names_are_unique_within_each_organization(self):
        second_org = Organization(name="Second Organization", slug="second")
        self.session.add(second_org)
        self.session.flush()

        self.session.add(Title(
            organization_id=second_org.id,
            name="L7",
            label="Second Org Entry Level",
            degree_requirement="BSc",
            base_salary_min=2000,
            base_salary_max=2800,
        ))
        self.session.commit()

        self.session.add(Title(
            organization_id=second_org.id,
            name="L7",
            label="Duplicate",
            degree_requirement="BSc",
            base_salary_min=2000,
            base_salary_max=2800,
        ))
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()

    def test_reference_counters_are_independent_per_organization(self):
        second_org = Organization(name="Second Organization", slug="second")
        self.session.add(second_org)
        self.session.flush()

        self.assertEqual(db.generate_employee_id(self.session), "EMP-0001")
        self.assertEqual(db.generate_employee_id(self.session), "EMP-0002")
        self.assertEqual(
            db.generate_employee_id(self.session, second_org.id),
            "EMP-0001",
        )


if __name__ == "__main__":
    unittest.main()
