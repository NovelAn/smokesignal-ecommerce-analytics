from pathlib import Path

from backend.config import settings
from backend.database.target_buyer_queries import TargetBuyerQueries


ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = ROOT / "backend/database/sql/ai_analysis_v2"


class RecordingDatabase:
    def __init__(self):
        self.sql = ""
        self.params = {}

    def execute_query(self, sql, params=None):
        self.sql = sql
        self.params = params or {}
        return []


def test_v2_priority_sql_includes_high_attention_and_v1_fallback():
    sql = (SQL_DIR / "get_priority_customers.sql").read_text(encoding="utf-8")

    assert "LEFT JOIN ai_analysis_v2_customer_state v2" in sql
    assert "v2.attention_priority IN ('urgent', 'high')" in sql
    assert "COALESCE(v2.current_sentiment_label, ai.sentiment_label, tb.sentiment_label)" in sql
    assert "v2.last_event_at > csl.updated_at" in sql
    assert "v2.buyer_nick IS NULL" in sql


def test_v2_list_and_count_share_the_same_default_filter():
    list_sql = (SQL_DIR / "get_priority_customers.sql").read_text(encoding="utf-8")
    count_sql = (SQL_DIR / "get_priority_customers_count.sql").read_text(encoding="utf-8")

    marker = "[[AND ("
    list_filter = marker + list_sql.split(marker, 1)[1].split("]]", 1)[0] + "]]"
    count_filter = marker + count_sql.split(marker, 1)[1].split("]]", 1)[0] + "]]"
    assert list_filter == count_filter


def test_priority_query_switch_is_off_by_default_and_explicit_when_enabled():
    assert settings.ai_analysis_v2_priority_enabled is False
    db = RecordingDatabase()
    queries = TargetBuyerQueries(db)

    queries.get_priority_customers(use_ai_v2=True)

    assert "ai_analysis_v2_customer_state" in db.sql
