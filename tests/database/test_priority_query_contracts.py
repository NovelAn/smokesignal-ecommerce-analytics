from pathlib import Path


SQL_DIR = Path(__file__).resolve().parents[2] / "backend" / "database" / "sql" / "target_buyers"


def read_sql(name: str) -> str:
    return (SQL_DIR / name).read_text(encoding="utf-8")


def test_priority_count_matches_service_reactivation_contract():
    sql = read_sql("get_priority_customers_count.sql")

    assert "LEFT JOIN customer_service_log csl" in sql
    assert "csl.status IN ('contacted', 'resolved')" in sql
    assert "incremental_sentiment_label = 'Negative'" in sql
    assert "target_buyers_precomputed_history" in sql


def test_churn_warning_is_unified_trackable_risk_query():
    sql = read_sql("get_churn_warning.sql")

    assert "情感转负" in sql
    assert "incremental_sentiment_label" in sql
    assert "service_status" in sql
    assert "customer_service_log" in sql
    assert "COUNT(*) OVER()" in sql


def test_monthly_trend_queries_use_one_snapshot_per_month():
    for filename in (
        "get_vic_pool_trend.sql",
        "get_vic_active_rate_trend.sql",
        "get_high_risk_trend.sql",
    ):
        sql = read_sql(filename)
        assert "MAX(snapshot_date)" in sql
        assert "monthly_latest" in sql


def test_dashboard_metrics_uses_latest_ai_sentiment_and_exposes_snapshot_time():
    sql = read_sql("get_dashboard_metrics.sql")

    assert "buyer_ai_analysis_cache" in sql
    assert "COALESCE(ai.sentiment_label, tb.sentiment_label)" in sql
    assert "last_updated" in sql
