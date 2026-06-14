"""VIC 群体画像聚合分析器

从多个 VIC 客户的 AI 画像中聚合兴趣、痛点和购买动机模式。
"""

from typing import Dict, List
from collections import Counter
import json


class VicPersonaAnalyzer:
    """VIC 群体画像聚合分析器"""

    # 购买动机模式关键词映射
    _MOTIVATION_PATTERNS: Dict[str, List[str]] = {
        "复购老客户": ["复购", "老客", "回购", "再次购买"],
        "新品尝鲜者": ["新品", "尝鲜", "最新", "限量"],
        "价格敏感型": ["优惠", "折扣", "活动", "促销"],
        "品质追求者": ["高端", "品质", "奢侈", "精品"],
    }

    def aggregate_interests(self, personas: List[Dict]) -> List[Dict]:
        """聚合所有 VIC 客户的 key_interests，按频率排序。

        Args:
            personas: 客户画像列表，每个包含 buyer_nick 和 key_interests。
                      key_interests 可以是 list 或 JSON 字符串。

        Returns:
            按频率降序排列的兴趣列表，每个包含 keyword, count, percentage。
        """
        all_interests = self._collect_field(personas, "key_interests")
        counter = Counter(all_interests)
        total = len(personas)
        if total == 0:
            return []
        return [
            {"keyword": kw, "count": c, "percentage": round(c / total * 100, 1)}
            for kw, c in counter.most_common()
        ]

    def aggregate_pain_points(self, personas: List[Dict]) -> List[Dict]:
        """聚合所有 VIC 客户的 pain_points，按频率排序。

        Args:
            personas: 客户画像列表，每个包含 buyer_nick 和 pain_points。
                      pain_points 可以是 list 或 JSON 字符串。

        Returns:
            按频率降序排列的痛点列表，每个包含 keyword, count, percentage。
        """
        all_pp = self._collect_field(personas, "pain_points")
        counter = Counter(all_pp)
        total = len(personas)
        if total == 0:
            return []
        return [
            {"keyword": kw, "count": c, "percentage": round(c / total * 100, 1)}
            for kw, c in counter.most_common()
        ]

    def extract_motivations(self, personas: List[Dict]) -> List[Dict]:
        """从 recommended_action 提取购买动机模式。

        Args:
            personas: 客户画像列表，每个包含 recommended_action 字符串。

        Returns:
            匹配到的动机模式列表，每个包含 pattern 和 count，按频率降序。
        """
        motivation_counts: Counter = Counter()
        for persona in personas:
            action = persona.get("recommended_action", "") or ""
            for pattern_name, keywords in self._MOTIVATION_PATTERNS.items():
                if any(kw in action for kw in keywords):
                    motivation_counts[pattern_name] += 1
        return [
            {"pattern": p, "count": c}
            for p, c in motivation_counts.most_common()
        ]

    async def analyze_vic_group(self) -> Dict:
        """分析所有 VIC 客户的群体画像（查询真实 DB）。

        Returns:
            包含 total_vic_count, key_interests, key_pain_points,
            purchase_motivations 的字典。
        """
        from backend.database import Database

        db = Database()
        query = """
            SELECT
                tb.buyer_nick,
                ai.key_interests,
                ai.pain_points,
                ai.recommended_action
            FROM target_buyers_precomputed tb
            JOIN buyer_ai_analysis_cache ai ON tb.buyer_nick = ai.buyer_nick
            WHERE tb.buyer_type IN ('VIC', 'BOTH')
              AND ai.key_interests IS NOT NULL
        """
        personas = db.execute_query(query)

        return {
            "total_vic_count": len(personas),
            "key_interests": self.aggregate_interests(personas),
            "key_pain_points": self.aggregate_pain_points(personas),
            "purchase_motivations": self.extract_motivations(personas),
        }

    # -- private helpers --

    @staticmethod
    def _collect_field(personas: List[Dict], field: str) -> List[str]:
        """从 personas 列表中提取某个字段的所有值。

        字段值可以是 list 或 JSON 字符串，统一转为 list 后展平。
        """
        items: List[str] = []
        for persona in personas:
            raw = persona.get(field)
            if not raw:
                continue
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    continue
            if isinstance(raw, list):
                items.extend(str(item) for item in raw if item)
        return items
