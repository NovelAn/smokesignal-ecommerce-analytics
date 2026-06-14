from datetime import date, timedelta
from typing import Dict, Tuple


class PeriodComparator:
    """时间对比计算器 — 计算等长对比期并对比关键指标变化"""

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
        """对比当期与对比期的关键指标（new_vic / churn_warning / vip_upgrades / sentiment_negative）。

        当前 _query_period_metrics 为占位实现，返回零值。
        真实指标需要 target_buyers_precomputed_history 快照对比，后续接入。
        """
        comp_start, comp_end = self.calculate_comparison_period(current_start, current_end)

        current_metrics = self._query_period_metrics(current_start, current_end)
        previous_metrics = self._query_period_metrics(comp_start, comp_end)

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
            change_pct = (change / previous_val * 100) if previous_val > 0 else 0.0
            metrics[metric_name] = {
                "current": current_val,
                "previous": previous_val,
                "change": change,
                "change_pct": round(change_pct, 1),
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

    def _query_period_metrics(
        self,
        start_date: date,
        end_date: date,
    ) -> Dict:
        """查询指定时间段的指标。

        占位实现：真实指标需从 target_buyers_precomputed_history 快照对比得出，
        涉及 VIP 等级/流失标签的时间序列，后续接入。当前返回零值占位。
        """
        return {
            "new_vic": 0,
            "churn_warning": 0,
            "vip_upgrades": 0,
            "sentiment_negative": 0,
        }
