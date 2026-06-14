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

    _INTEREST_THEMES: Dict[str, List[str]] = {
        "复购与品牌忠诚": ["复购", "回购", "老客", "忠诚", "跨年"],
        "促销敏感": ["促销", "优惠", "折扣", "活动", "满减", "价格敏感", "大促", "季末", "节点"],
        "正价与品质偏好": ["正价", "品质", "高端", "奢侈", "工艺", "经典", "限量", "限定", "收藏", "全价"],
        "成衣偏好": ["成衣", "外套", "梭织", "针织", "knitwear", "readywear", "woven", "夹克", "衬衫", "裤"],
        "烟斗与烟具偏好": ["烟斗", "烟具", "打火机", "雪茄", "吸烟"],
        "鞋履偏好": ["鞋", "靴", "loafer", "sneaker", "footwear"],
        "配饰偏好": ["配饰", "皮带", "腰带", "钱包", "包袋", "领带", "围巾", "眼镜"],
        "跨品类购买": ["跨品类", "多品类", "品类广", "全品类", "total look", "分散"],
        "静默或集中购买": ["静默", "沉默", "批量", "集中购买", "集中下单", "大额单次", "直接下单"],
    }

    _PAIN_THEMES: Dict[str, List[str]] = {
        "留存与流失风险": ["流失", "沉睡", "召回", "活跃", "复购", "长期未购", "未消费", "忠诚", "粘性", "黏性", "购买动力", "品牌记忆"],
        "互动数据不足": ["缺聊天", "无聊天", "聊天记录", "互动不足", "沟通不足", "沟通少", "沟通沉默", "数据不足", "画像不足", "需求难捕捉", "主动沟通"],
        "VIP 等级不匹配": ["vip漏升", "漏升", "等级不匹配", "会员等级", "vip不匹配"],
        "折扣依赖": ["折扣依赖", "促销依赖", "价格敏感", "优惠依赖", "非大促", "大促/季末", "正价心智"],
        "品类过度集中": ["品类集中", "单一品类", "品类单一", "购买集中", "跨品类弱", "品类弱", "品类收窄", "品类回缩", "覆盖窄", "过于集中"],
        "退款与退换风险": ["退款", "退货", "换货", "退换"],
        "尺码与适配": ["尺码", "合身", "适配", "尺寸"],
        "服务与履约": ["物流", "发货", "配送", "客服", "服务", "售后", "库存", "缺货", "取件码", "保养", "维护"],
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

    def aggregate_interest_themes(self, personas: List[Dict]) -> List[Dict]:
        return self._aggregate_themes(personas, "key_interests", self._INTEREST_THEMES, "其他偏好")

    def aggregate_pain_themes(self, personas: List[Dict]) -> List[Dict]:
        return self._aggregate_themes(personas, "pain_points", self._PAIN_THEMES, "其他风险")

    def build_group_result(self, personas: List[Dict]) -> Dict:
        interests = self.aggregate_interest_themes(personas)
        pain_points = self.aggregate_pain_themes(personas)
        raw_label_count = len(self._collect_field(personas, "key_interests")) + len(
            self._collect_field(personas, "pain_points")
        )
        summarized_interests = [item for item in interests if item["keyword"] != "其他偏好"]
        summarized_pains = [item for item in pain_points if item["keyword"] != "其他风险"]
        top_interest_item = summarized_interests[0] if summarized_interests else None
        top_pain_item = summarized_pains[0] if summarized_pains else None
        top_interest = top_interest_item["keyword"] if top_interest_item else "偏好数据不足"
        top_pain = top_pain_item["keyword"] if top_pain_item else "风险数据不足"
        bullets = []
        if top_interest_item:
            bullets.append(f"最普遍兴趣为{top_interest}，覆盖 {top_interest_item['percentage']}% 的 VIC 样本。")
        if top_pain_item:
            bullets.append(f"首要关注点为{top_pain}，涉及 {top_pain_item['count']} 位客户。")
        if not bullets:
            bullets.append("当前可用画像标签不足，暂无法形成稳定群体结论。")

        return {
            "total_vic_count": len(personas),
            "key_interests": interests,
            "key_pain_points": pain_points,
            "purchase_motivations": self.extract_motivations(personas),
            "summary": {
                "headline": f"VIC 群体以{top_interest}为主要偏好，当前最需关注{top_pain}",
                "bullets": bullets,
            },
            "raw_label_count": raw_label_count,
            "aggregated_theme_count": len(interests) + len(pain_points),
        }

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
                ai.persona_key_interests AS key_interests,
                ai.persona_pain_points AS pain_points,
                ai.persona_recommended_action AS recommended_action
            FROM target_buyers_precomputed tb
            JOIN buyer_ai_analysis_cache ai ON tb.buyer_nick = ai.buyer_nick
            WHERE tb.buyer_type IN ('VIC', 'BOTH')
              AND ai.persona_key_interests IS NOT NULL
        """
        personas = db.execute_query(query)

        return self.build_group_result(personas)

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

    def _aggregate_themes(
        self,
        personas: List[Dict],
        field: str,
        theme_rules: Dict[str, List[str]],
        fallback_theme: str,
    ) -> List[Dict]:
        if not personas:
            return []

        theme_customers: Dict[str, set] = {}
        theme_examples: Dict[str, Counter] = {}
        for index, persona in enumerate(personas):
            customer_key = persona.get("buyer_nick") or f"row-{index}"
            labels = self._field_values(persona.get(field))
            for label in labels:
                theme = self._match_theme(label, theme_rules) or fallback_theme
                theme_customers.setdefault(theme, set()).add(customer_key)
                theme_examples.setdefault(theme, Counter())[label] += 1

        total = len(personas)
        results = []
        for theme, customers in theme_customers.items():
            count = len(customers)
            results.append({
                "keyword": theme,
                "count": count,
                "percentage": round(count / total * 100, 1),
                "examples": [label for label, _ in theme_examples[theme].most_common(3)],
            })
        return sorted(
            results,
            key=lambda item: (item["keyword"] == fallback_theme, -item["count"], item["keyword"]),
        )

    @staticmethod
    def _field_values(raw: object) -> List[str]:
        if not raw:
            return []
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return []
        if not isinstance(raw, list):
            return []
        return [str(item).strip() for item in raw if str(item).strip()]

    @staticmethod
    def _match_theme(label: str, theme_rules: Dict[str, List[str]]) -> str | None:
        normalized = label.lower().replace(" ", "")
        for theme, keywords in theme_rules.items():
            if any(keyword.lower().replace(" ", "") in normalized for keyword in keywords):
                return theme
        return None
