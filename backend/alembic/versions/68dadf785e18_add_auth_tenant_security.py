"""add auth tenant security

Revision ID: 68dadf785e18
Revises: d99aca40fca5
Create Date: 2026-11-28 16:03:13.210483

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68dadf785e18'
down_revision: Union[str, Sequence[str], None] = 'd99aca40fca5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    op.add_column(
        sa.sql.quoted_name("system_user", True),
        sa.Column("auth_user_id", sa.Uuid(as_uuid=False), nullable=True),
    )
    op.create_index(
        "ix_system_user_auth_user_id",
        sa.sql.quoted_name("system_user", True),
        ["auth_user_id"],
        unique=True,
    )
    if bind.dialect.name != "postgresql":
        return

    op.create_foreign_key(
        "fk_system_user_auth_user",
        sa.sql.quoted_name("system_user", True),
        "users",
        ["auth_user_id"],
        ["id"],
        source_schema="public",
        referent_schema="auth",
        ondelete="SET NULL",
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'myhr_api') THEN
                CREATE ROLE myhr_api NOLOGIN NOINHERIT;
            END IF;
        END
        $$;
        GRANT myhr_api TO postgres;
        GRANT USAGE ON SCHEMA public TO myhr_api;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO myhr_api;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO myhr_api;
        """
    )

    tenant_tables = (
        "org_unit",
        "reference_counter",
        "system_user",
        "title",
        "audit_log",
        "commendation",
        "employee",
        "promotion_rule",
        "performance_score",
        "promotion_history",
        "salary_increment_history",
        "sanction",
    )
    for table in tenant_tables:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(
            f"""
            CREATE POLICY myhr_tenant_access ON "{table}"
            FOR ALL TO myhr_api
            USING (
                organization_id = NULLIF(
                    current_setting('request.jwt.claims', true)::jsonb
                        ->> 'organization_id',
                    ''
                )::integer
            )
            WITH CHECK (
                organization_id = NULLIF(
                    current_setting('request.jwt.claims', true)::jsonb
                        ->> 'organization_id',
                    ''
                )::integer
            )
            """
        )

    op.execute("ALTER TABLE organization ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE organization FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY myhr_tenant_access ON organization
        FOR ALL TO myhr_api
        USING (
            id = NULLIF(
                current_setting('request.jwt.claims', true)::jsonb
                    ->> 'organization_id',
                ''
            )::integer
        )
        WITH CHECK (
            id = NULLIF(
                current_setting('request.jwt.claims', true)::jsonb
                    ->> 'organization_id',
                ''
            )::integer
        )
        """
    )
    op.execute("ALTER TABLE commendation_employee ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE commendation_employee FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY myhr_tenant_access ON commendation_employee
        FOR ALL TO myhr_api
        USING (
            EXISTS (
                SELECT 1 FROM commendation
                WHERE commendation.id = commendation_employee.commendation_id
            )
            AND EXISTS (
                SELECT 1 FROM employee
                WHERE employee.id = commendation_employee.employee_id
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1 FROM commendation
                WHERE commendation.id = commendation_employee.commendation_id
            )
            AND EXISTS (
                SELECT 1 FROM employee
                WHERE employee.id = commendation_employee.employee_id
            )
        )
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in (
            "organization",
            "org_unit",
            "reference_counter",
            "system_user",
            "title",
            "audit_log",
            "commendation",
            "employee",
            "promotion_rule",
            "commendation_employee",
            "performance_score",
            "promotion_history",
            "salary_increment_history",
            "sanction",
        ):
            op.execute(f'DROP POLICY IF EXISTS myhr_tenant_access ON "{table}"')
            op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
        op.execute("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM myhr_api")
        op.execute("REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM myhr_api")
        op.execute("REVOKE USAGE ON SCHEMA public FROM myhr_api")
        op.execute("REVOKE myhr_api FROM postgres")
        op.drop_constraint(
            "fk_system_user_auth_user",
            sa.sql.quoted_name("system_user", True),
            type_="foreignkey",
        )
        op.execute("DROP ROLE IF EXISTS myhr_api")
    op.drop_index(
        "ix_system_user_auth_user_id",
        table_name=sa.sql.quoted_name("system_user", True),
    )
    op.drop_column(sa.sql.quoted_name("system_user", True), "auth_user_id")
