from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "backend" / "database" / "migrations" / "20260614_add_service_workstream.sql"


def test_service_workstream_migration_is_idempotent_and_preserves_priority_rows():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "ADD COLUMN workstream" in sql
    assert "UPDATE customer_service_log" in sql
    assert "'priority'" in sql
    assert "UNIQUE KEY" in sql
    assert "buyer_nick, workstream" in sql.replace("`", "")


def test_priority_queries_only_join_priority_service_records():
    sql_dir = ROOT / "backend" / "database" / "sql" / "target_buyers"
    for filename in (
        "get_priority_customers.sql",
        "get_priority_customers_count.sql",
        "get_churn_warning.sql",
    ):
        sql = (sql_dir / filename).read_text(encoding="utf-8")
        assert "workstream = 'priority'" in sql
