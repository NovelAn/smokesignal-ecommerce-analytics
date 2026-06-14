"""
Rule-Based Analyzer - 规则引擎兜底客户画像分析（L3 fallback）

当 AI 模型（MiniMax / DeepSeek）不可用时使用规则推断客户画像。
本模块对齐 persona AI prompt（backend/ai/prompts/persona_inference.py）的五维度框架：
客户类型 / 忠诚度 / 活跃度 / 成熟度 / 核心关注点，并产出结论式（非模板）文案。

注意：persona 结果在 analyzer_orchestrator 会再过一道 ground_persona_analysis_v3
（补全品类/折扣/购买时机等 trait_dimensions、校验 summary 数字），因此本模块聚焦
AI prompt 明令要求而 ground 不覆盖的部分：维度标签（customer_tags）+ 去模板化 summary。
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from backend.ai.data_extractor import detect_expert_signal, detect_rookie_signal


class RuleBasedAnalyzer:
    """基于规则的客户画像分析器（兜底方案），对齐 AI persona 五维度框架。"""

    def analyze(
        self,
        profile: Dict,
        chats: List[Dict],
        orders: List[Dict],
    ) -> Dict[str, Any]:
        """规则推断客户画像。

        Args:
            profile: 客户档案（预计算表字段）
            chats: 聊天记录列表（每条含 content）
            orders: 订单列表（每条含 category / order_date 等，字段容错）

        Returns:
            summary / key_interests / pain_points / recommended_action /
            confidence_level / customer_tags（五维度）
        """
        customer_type = self._customer_type(profile, orders)
        loyalty = self._loyalty(profile, orders)
        activity = self._activity(profile)
        maturity = self._maturity(chats)
        focus = self._focus(profile)

        return {
            "summary": self._build_summary(profile, customer_type, loyalty, activity, maturity),
            "key_interests": self._build_interests(customer_type, focus),
            "pain_points": self._build_pain_points(profile, focus),
            "recommended_action": self._build_action(customer_type, loyalty, focus),
            "confidence_level": self._confidence(profile, orders, chats),
            "customer_tags": {
                "客户类型": customer_type,
                "忠诚度": loyalty,
                "活跃度": activity,
                "成熟度": maturity,
                "核心关注点": focus,
            },
        }

    # ------------------------------------------------------------------
    # Dimension calculations
    # ------------------------------------------------------------------
    @staticmethod
    def _categories(orders: List[Dict]) -> List[str]:
        out = []
        for o in orders or []:
            if not isinstance(o, dict):
                continue
            c = (o.get("category") or o.get("product_category") or o.get("cat") or "")
            c = str(c).strip()
            if c:
                out.append(c)
        return out

    @classmethod
    def _customer_type(cls, profile: Dict, orders: List[Dict]) -> str:
        """客户类型：Total Look / 品类专注 / 探索型（对齐 persona_inference 框架）。"""
        cats = cls._categories(orders)
        if not cats:
            top = (profile.get("top_category") or "").strip()
            return f"品类专注-{top}" if top else "探索型"
        cnt = Counter(cats)
        distinct = len(cnt)
        top_cat, top_n = cnt.most_common(1)[0]
        top_ratio = top_n / len(cats)
        # Total Look: 3+ 品类
        if distinct >= 3:
            return "Total Look"
        # 品类专注: 单一品类占比 >= 80%
        if top_ratio >= 0.8:
            return f"品类专注-{top_cat}"
        return "探索型"

    @staticmethod
    def _order_years(orders: List[Dict]) -> set:
        years = set()
        for o in orders or []:
            if not isinstance(o, dict):
                continue
            d = str(o.get("order_date") or o.get("pay_time") or o.get("created_at") or "")
            if len(d) >= 4 and d[:4].isdigit():
                years.add(d[:4])
        return years

    @classmethod
    def _loyalty(cls, profile: Dict, orders: List[Dict]) -> str:
        """忠诚度：高（跨年度复购/VIP 高）/ 中 / 待培养。"""
        vip = profile.get("vip_level", "") or ""
        l1y = float(profile.get("l1y_netsales", 0) or 0)
        years = cls._order_years(orders)
        if len(years) >= 2 or vip in ("V3", "V2") or l1y >= 100000:
            return "高忠诚"
        if l1y >= 30000 or vip in ("V1", "V0"):
            return "中忠诚"
        return "待培养"

    @staticmethod
    def _activity(profile: Dict) -> str:
        """活跃度：近 6 月有消费即中活跃（对齐 AI"近期有购买不等于流失"原则）。"""
        l6m = float(profile.get("l6m_netsales", 0) or 0)
        if l6m > 0:
            return "中活跃"
        return "低活跃"

    @staticmethod
    def _maturity(chats: List[Dict]) -> str:
        """成熟度：结合聊天专业/新手信号。"""
        rookie = sum(1 for c in chats if detect_rookie_signal((c or {}).get("content", "")))
        expert = sum(1 for c in chats if detect_expert_signal((c or {}).get("content", "")))
        if expert >= 3:
            return "资深"
        if rookie >= 3:
            return "新手"
        return "熟悉"

    @staticmethod
    def _focus(profile: Dict) -> str:
        """核心关注点。"""
        refund_rate = float(profile.get("l6m_refund_rate", 0) or 0)
        if refund_rate > 0.1:
            return "品质保障"
        top = (profile.get("top_category") or "").strip()
        if top:
            return f"{top}品类"
        return "价格优惠"

    # ------------------------------------------------------------------
    # Copy builders (conclusion-style, not templated — aligned with AI prompt)
    # ------------------------------------------------------------------
    @staticmethod
    def _build_summary(profile, customer_type, loyalty, activity, maturity) -> str:
        vip = profile.get("vip_level", "") or ""
        l1y = float(profile.get("l1y_netsales", 0) or 0)
        l6m = float(profile.get("l6m_netsales", 0) or 0)
        parts = []
        if vip:
            parts.append(f"{vip}客户")
        parts.append(customer_type)
        parts.append(f"{loyalty}/{activity}/{maturity}")
        if l1y > 0:
            parts.append(f"近1年消费¥{l1y:,.0f}")
        if l6m > 0:
            parts.append(f"近6月¥{l6m:,.0f}")
        return "，".join(parts) + "。"

    @staticmethod
    def _build_interests(customer_type: str, focus: str) -> List[str]:
        interests = [f"{focus}相关产品"]
        if customer_type == "Total Look":
            interests += ["跨品类搭配", "新品优先体验"]
        elif customer_type.startswith("品类专注"):
            interests += ["同品类升级款", "专业配件"]
        else:
            interests += ["多品类体验", "入门推荐"]
        return interests[:4]

    @staticmethod
    def _build_pain_points(profile: Dict, focus: str) -> List[str]:
        refund_rate = float(profile.get("l6m_refund_rate", 0) or 0)
        pts = []
        if refund_rate > 0.1:
            pts.append("对品质/尺码有顾虑，退款率偏高")
        if focus == "品质保障":
            pts.append("需要正品与品质承诺")
        pts.append("需要更精准的个性化推荐")
        return pts[:3]

    @staticmethod
    def _build_action(customer_type: str, loyalty: str, focus: str) -> str:
        if loyalty == "高忠诚":
            base = "优先推荐新品与稀缺款，VIP 专属服务跟进"
        elif loyalty == "待培养":
            base = "主动沟通了解需求，引导首次复购"
        else:
            base = "按当前偏好推荐，维持复购节奏"
        if customer_type == "Total Look":
            base += "，配套单品打造完整造型"
        return base

    @staticmethod
    def _confidence(profile: Dict, orders: List[Dict], chats: List[Dict]) -> str:
        if orders or profile.get("l1y_netsales") or chats:
            return "中"
        return "低"
