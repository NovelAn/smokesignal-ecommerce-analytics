"""Customer trend data aggregator.

Aggregates VIC pool size, active rate, and high-risk trends
from target_buyers_precomputed_history snapshots.
"""

from typing import Any, Dict, List, Optional


class TrendAggregator:
    """客户趋势数据聚合器"""

    def __init__(self, queries: Optional[Any] = None):
        self.queries = queries

    def _get_queries(self):
        if self.queries is None:
            from backend.database import Database
            from backend.database.target_buyer_queries import TargetBuyerQueries

            self.queries = TargetBuyerQueries(Database())
        return self.queries

    def format_vic_pool_trend(self, raw_data: List[Dict]) -> List[Dict]:
        """格式化 VIC 池规模趋势（按买家类型分层）。

        Passes through raw query results; future versions may
        add derived fields (e.g., totals, period-over-period deltas).
        """
        return list(raw_data)

    def calculate_active_rate(self, total_vic: int, active_vic: int) -> float:
        """活跃率 = active / total * 100，total=0 时返回 0.0。"""
        if total_vic == 0:
            return 0.0
        return round(active_vic / total_vic * 100, 1)

    def format_active_rate_trend(self, raw_data: List[Dict]) -> List[Dict]:
        """为每条记录追加 active_rate 字段。"""
        result: List[Dict] = []
        for item in raw_data:
            total = item.get("total_vic", 0)
            active = item.get("active_vic", 0)
            result.append({
                "month": item["month"],
                "total_vic": total,
                "active_vic": active,
                "active_rate": self.calculate_active_rate(total, active),
            })
        return result

    async def get_customer_trends(self, months: int = 6) -> Dict:
        """从历史快照表聚合趋势数据。

        NOTE:
        - 历史表无 last_chat_date 列，活跃率仅基于 last_purchase_date
          （当月有购买记录的 VIC 占比）。
        - churn_risk 值为中文（'高'/'中'/'低'）。
        - sentiment_trend 暂为空（历史表无情感字段）。
        """
        queries = self._get_queries()
        pool_data = queries.get_vic_pool_trend(months)
        active_raw = queries.get_vic_active_rate_trend(months)
        risk_data = queries.get_high_risk_trend(months)

        return {
            "vic_pool_trend": self.format_vic_pool_trend(pool_data),
            "vic_active_rate_trend": self.format_active_rate_trend(active_raw),
            "high_risk_trend": risk_data,
            "sentiment_trend": [],
        }
