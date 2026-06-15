from datetime import date, timedelta
from typing import Any, Dict, Optional, Tuple


class PeriodComparator:
    """时间对比计算器 — 计算等长对比期并对比关键指标变化"""

    def __init__(self, queries: Optional[Any] = None):
        self.queries = queries

    def _get_queries(self):
        if self.queries is None:
            from backend.database import Database
            from backend.database.target_buyer_queries import TargetBuyerQueries

            self.queries = TargetBuyerQueries(Database())
        return self.queries

    def calculate_comparison_period(
        self,
        current_start: date,
        current_end: date,
    ) -> Tuple[date, date]:
        """计算等长对比期（T0 = T1 长度的前一段，紧邻 T1 前一天）。

        Examples:
            5/1–5/31 (31天) → 3/31–4/30 (31天)
            6/10–6/10 (1天) → 6/9–6/9 (1天)
        """
        period_length = (current_end - current_start).days + 1
        comp_end = current_start - timedelta(days=1)
        comp_start = comp_end - timedelta(days=period_length - 1)
        return comp_start, comp_end

    async def compare_metrics(
        self,
        current_start: date,
        current_end: date,
    ) -> Dict:
        """对比当期与对比期的真实快照指标。"""
        comp_start, comp_end = self.calculate_comparison_period(current_start, current_end)

        queries = self._get_queries()
        current_metrics = queries.get_period_comparison_metrics(
            current_start, current_end
        )
        previous_metrics = queries.get_period_comparison_metrics(
            comp_start, comp_end
        )

        metrics: Dict[str, Dict] = {}
        for metric_name in [
            "new_vic",
            "churn_warning",
            "vip_upgrades",
            "sentiment_negative",
        ]:
            current_val = current_metrics.get(metric_name, 0)
            previous_val = previous_metrics.get(metric_name, 0)
            change = current_val - previous_val
            # previous=0 时无法算百分比：change>0 是纯新增（返回 None，前端显示"新增"），
            # change=0 则无变化。None 比 0.0% 准确，避免"新增 5 (0.0%)"的误导。
            change_pct = (change / previous_val * 100) if previous_val > 0 else None
            metrics[metric_name] = {
                "current": current_val,
                "previous": previous_val,
                "change": change,
                "change_pct": round(change_pct, 1) if change_pct is not None else None,
            }

        return {
            "current_period": {
                "start_date": current_start.isoformat(),
                "end_date": current_end.isoformat(),
            },
            "comparison_period": {
                "start_date": comp_start.isoformat(),
                "end_date": comp_end.isoformat(),
            },
            "metrics": metrics,
        }
