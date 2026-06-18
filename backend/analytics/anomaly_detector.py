"""异常客户检测器 — 识别高价值客户中的风险信号。

检测规则：
  - sentiment_negative: 上月 Positive → 本月 Negative (high severity)
  - purchase_interval_long: 距上次购买 > 180 天 (medium severity)
  - chat_frequency_drop: 本月聊天量 < 历史月均的 50% 且月均 >= 10 (medium severity)
"""

from typing import Dict, List, Optional
from datetime import date, datetime


def _coerce_to_date(value) -> Optional[date]:
    """将多种日期表示统一转为 date，无法解析时返回 None。

    支持：
      - date / datetime（直接取 .date()）
      - 'YYYY-MM-DD'
      - 'YYYY-MM-DD HH:MM:SS'（截取日期部分）
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        s = value.strip()
        # 截取 'YYYY-MM-DD HH:MM:SS' 的日期部分
        date_part = s.split(" ")[0]
        for fmt in ("%Y-%m-%d",):
            try:
                return datetime.strptime(date_part, fmt).date()
            except ValueError:
                continue
    return None


class AnomalyDetector:
    """异常客户检测器"""

    def detect_anomalies(self, customers: List[Dict]) -> List[Dict]:
        """对一组客户记录运行所有异常检测规则。

        Args:
            customers: 客户数据字典列表，每条需包含检测规则所需的字段。

        Returns:
            检测到的异常记录列表，每条包含 buyer_nick、vip_level、
            anomaly_type、severity、anomaly_reason 等字段。
        """
        anomalies: List[Dict] = []
        for customer in customers:
            for check in (
                self._check_sentiment_shift,
                self._check_purchase_interval,
                self._check_chat_frequency,
            ):
                found = check(customer)
                if found:
                    anomalies.append(found)
        return anomalies

    def _base_record(
        self, customer: Dict, anomaly_type: str, reason: str, severity: str
    ) -> Dict:
        """构造统一的异常记录字典。"""
        return {
            "buyer_nick": customer.get("buyer_nick"),
            "vip_level": customer.get("vip_level", "Non-VIP"),
            "anomaly_type": anomaly_type,
            "anomaly_reason": reason,
            "last_purchase_date": customer.get("last_purchase_date"),
            "last_chat_date": customer.get("last_chat_date"),
            "severity": severity,
        }

    def _check_sentiment_shift(self, customer: Dict) -> Optional[Dict]:
        """检测情感负向转变：上月 Positive → 本月 Negative。"""
        if (
            customer.get("previous_sentiment") == "Positive"
            and customer.get("current_sentiment") == "Negative"
        ):
            return self._base_record(
                customer,
                "sentiment_negative",
                "上月 Positive → 本月 Negative",
                "high",
            )
        return None

    def _check_purchase_interval(self, customer: Dict) -> Optional[Dict]:
        """检测购买间隔过长：距上次购买 > 180 天。"""
        last_purchase = customer.get("last_purchase_date")
        if not last_purchase:
            return None
        last_purchase = _coerce_to_date(last_purchase)
        if last_purchase is None:
            return None
        days_since = (date.today() - last_purchase).days
        if days_since > 180:
            return self._base_record(
                customer,
                "purchase_interval_long",
                f"距上次购买 {days_since} 天，超过 180 天",
                "medium",
            )
        return None

    def _check_chat_frequency(self, customer: Dict) -> Optional[Dict]:
        """检测聊天频率骤降：本月聊天量 < 历史月均的 50% 且月均 >= 10。"""
        current = customer.get("current_month_chats", 0)
        avg = customer.get("avg_monthly_chats", 0)
        if avg >= 10 and current < avg * 0.5:
            return self._base_record(
                customer,
                "chat_frequency_drop",
                f"本月聊天 {current} 条，历史月均 {avg} 条",
                "medium",
            )
        return None

    async def get_all_anomalies(self) -> Dict:
        """从 DB 拉取高价值客户并检测异常。

        查询 target_buyers_precomputed + buyer_ai_analysis_cache，
        对 VIC/BOTH/SMOKER 类型的客户执行全部检测规则。

        NOTE: previous_sentiment 暂以 "Positive" 为基线，仅 current_sentiment=Negative
        触发。完整的 T0/T1 情感对比需 target_buyers_precomputed_history 表，后续接入。

        Returns:
            包含 anomalies 列表（最多 50 条）和 total_count 的字典。
        """
        from backend.database import Database

        db = Database()
        query = """
            SELECT tb.buyer_nick, tb.vip_level, tb.last_purchase_date,
                   tb.last_chat_date, ai.sentiment_label AS current_sentiment
            FROM target_buyers_precomputed tb
            JOIN buyer_ai_analysis_cache ai ON tb.buyer_nick = ai.buyer_nick
            WHERE tb.buyer_type IN ('VIC', 'BOTH', 'SMOKER')
        """
        rows = db.execute_query(query)

        customers = [
            {
                "buyer_nick": r["buyer_nick"],
                "vip_level": r.get("vip_level", "Non-VIP"),
                "last_purchase_date": (
                    str(r["last_purchase_date"]) if r.get("last_purchase_date") else None
                ),
                "last_chat_date": (
                    str(r["last_chat_date"]) if r.get("last_chat_date") else None
                ),
                "previous_sentiment": "Positive",
                "current_sentiment": r.get("current_sentiment"),
            }
            for r in rows
        ]

        anomalies = self.detect_anomalies(customers)
        return {"anomalies": anomalies[:50], "total_count": len(anomalies)}
