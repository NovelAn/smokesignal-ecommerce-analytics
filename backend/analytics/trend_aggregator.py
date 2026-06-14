"""Customer trend data aggregator.

Aggregates VIC pool size, active rate, and high-risk trends
from target_buyers_precomputed_history snapshots.
"""

from typing import Dict, List


class TrendAggregator:
    """客户趋势数据聚合器"""

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
        from backend.database import Database

        db = Database()

        # VIC 池规模趋势（按 buyer_type 分层）
        pool_data = db.execute_query(
            """
            SELECT DATE_FORMAT(snapshot_date, '%%Y-%%m') AS month,
                   SUM(CASE WHEN buyer_type='SMOKER' THEN 1 ELSE 0 END) AS SMOKER,
                   SUM(CASE WHEN buyer_type='VIC' THEN 1 ELSE 0 END) AS VIC,
                   SUM(CASE WHEN buyer_type='BOTH' THEN 1 ELSE 0 END) AS `BOTH`
            FROM target_buyers_precomputed_history
            WHERE snapshot_date >= DATE_SUB(CURDATE(), INTERVAL %s MONTH)
            GROUP BY DATE_FORMAT(snapshot_date, '%%Y-%%m')
            ORDER BY month
            """,
            (months,),
        )

        # VIC 活跃率趋势（当月有购买 = 活跃）
        active_raw = db.execute_query(
            """
            SELECT month, COUNT(*) AS total_vic,
                   SUM(is_active) AS active_vic
            FROM (
                SELECT DATE_FORMAT(snapshot_date, '%%Y-%%m') AS month,
                       CASE WHEN DATE_FORMAT(last_purchase_date, '%%Y-%%m')
                                = DATE_FORMAT(snapshot_date, '%%Y-%%m')
                            THEN 1 ELSE 0 END AS is_active
                FROM target_buyers_precomputed_history
                WHERE buyer_type IN ('VIC', 'BOTH')
                  AND snapshot_date >= DATE_SUB(CURDATE(), INTERVAL %s MONTH)
            ) t
            GROUP BY month
            ORDER BY month
            """,
            (months,),
        )

        # 高风险客户趋势（churn_risk 中文值）
        risk_data = db.execute_query(
            """
            SELECT DATE_FORMAT(snapshot_date, '%%Y-%%m') AS month,
                   COUNT(*) AS high_risk_count
            FROM target_buyers_precomputed_history
            WHERE churn_risk = '高'
              AND snapshot_date >= DATE_SUB(CURDATE(), INTERVAL %s MONTH)
            GROUP BY DATE_FORMAT(snapshot_date, '%%Y-%%m')
            ORDER BY month
            """,
            (months,),
        )

        return {
            "vic_pool_trend": self.format_vic_pool_trend(pool_data),
            "vic_active_rate_trend": self.format_active_rate_trend(active_raw),
            "high_risk_trend": risk_data,
            "sentiment_trend": [],
        }
