from io import StringIO
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_initial_migration_builds_tenant_ready_schema(tmp_path, monkeypatch):
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("MYHR_DATABASE_URL", database_url)

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    expected_tenant_tables = {
        "employee",
        "org_unit",
        "title",
        "promotion_rule",
        "commendation",
        "sanction",
        "promotion_history",
        "salary_increment_history",
        "performance_score",
        "audit_log",
        "system_user",
    }
    assert expected_tenant_tables.issubset(set(inspector.get_table_names()))
    for table_name in expected_tenant_tables:
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        assert "organization_id" in columns

    system_user_columns = {
        column["name"] for column in inspector.get_columns("system_user")
    }
    assert "auth_user_id" in system_user_columns
    auth_indexes = {
        index["name"]: index for index in inspector.get_indexes("system_user")
    }
    assert auth_indexes["ix_system_user_auth_user_id"]["unique"] == 1

    with engine.connect() as connection:
        default_org = connection.execute(
            text("SELECT id, slug FROM organization")
        ).one()
    assert default_org == (1, "default")

    command.downgrade(config, "base")
    assert "organization" not in inspect(engine).get_table_names()


def test_postgres_migration_quotes_user_table_and_enables_tenant_rls(monkeypatch):
    monkeypatch.setenv(
        "MYHR_DATABASE_URL",
        "postgresql+psycopg://user:password@example.test/postgres",
    )
    output = StringIO()
    config = Config(str(BACKEND_ROOT / "alembic.ini"), output_buffer=output)

    command.upgrade(config, "head", sql=True)

    sql = output.getvalue()
    assert 'CREATE TABLE "system_user"' in sql
    assert 'REFERENCES "system_user"' in sql
    assert "REFERENCES system_user" not in sql
    assert "GRANT myhr_api TO postgres" in sql
    assert sql.count("ENABLE ROW LEVEL SECURITY") == 14
    assert sql.count("CREATE POLICY myhr_tenant_access") == 14
