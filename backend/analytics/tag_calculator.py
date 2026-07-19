"""
Tag calculation logic for buyer segmentation
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
import threading
import time


_TAG_CONFIG_CACHE: Dict[str, Any] = {}
_TAG_CONFIG_CACHE_TS: float = 0.0
_TAG_CONFIG_CACHE_TTL: int = 300  # 5 分钟
_TAG_CONFIG_LOCK = threading.Lock()

# 默认值, 与 create_tag_config.sql 的 seed 完全一致
# 用于 DB 不可达 / tag_config 表尚未初始化时的兜底
TAG_CONFIG_DEFAULTS: Dict[str, float] = {
    "vip_v0_min": 30000,
    "vip_v1_min": 50000,
    "vip_v2_min": 150000,
    "vip_v3_min": 450000,
    "churn_high_days_since_chat": 180,
    "churn_medium_days_since_chat": 90,
    "discount_high_ratio": 0.7,
    "discount_medium_ratio": 0.4,
    "lifecycle_new_customer_days": 90,
    "lifecycle_mature_min_netsales": 50000,
    "lifecycle_churn_days_since_purchase": 365,
}


def get_tag_config() -> Dict[str, float]:
    """读取 tag_config 表 (5 分钟内存缓存, 失败时返回默认)."""
    global _TAG_CONFIG_CACHE, _TAG_CONFIG_CACHE_TS
    now = time.time()
    if _TAG_CONFIG_CACHE and (now - _TAG_CONFIG_CACHE_TS) < _TAG_CONFIG_CACHE_TTL:
        return _TAG_CONFIG_CACHE
    with _TAG_CONFIG_LOCK:
        # 双重检查, 避免并发重复查 DB
        if _TAG_CONFIG_CACHE and (time.time() - _TAG_CONFIG_CACHE_TS) < _TAG_CONFIG_CACHE_TTL:
            return _TAG_CONFIG_CACHE
        try:
            from backend.database import Database
            from backend.config import settings

            db_name = settings.db_name_to_use if settings.db_name_to_use else "aliyunDB"
            db = Database(db_name=db_name)
            rows = db.execute_query("SELECT config_key, config_value FROM tag_config")
            config = {row["config_key"]: float(row["config_value"]) for row in rows}
            if config:
                _TAG_CONFIG_CACHE = config
                _TAG_CONFIG_CACHE_TS = time.time()
                return config
        except Exception as e:
            logging.warning(f"[TagConfig] Failed to load tag_config: {e}; using defaults")
        # 兜底: 返回默认
        _TAG_CONFIG_CACHE = dict(TAG_CONFIG_DEFAULTS)
        _TAG_CONFIG_CACHE_TS = time.time()
        return _TAG_CONFIG_CACHE


def invalidate_tag_config_cache() -> None:
    """手动失效缓存 (PUT 端点调用)."""
    global _TAG_CONFIG_CACHE, _TAG_CONFIG_CACHE_TS
    with _TAG_CONFIG_LOCK:
        _TAG_CONFIG_CACHE = {}
        _TAG_CONFIG_CACHE_TS = 0.0


class TagCalculator:
    """Calculate buyer tags based on order and chat data"""

    @staticmethod
    def calculate_vip_level(rolling_netsales: float, config: Optional[Dict[str, float]] = None) -> str:
        """
        Calculate VIP level based on rolling 24 months netsales (P2: thresholds from tag_config)

        Default thresholds (from TAG_CONFIG_DEFAULTS):
        - Non-VIP: < 30,000
        - V0: 30,000 - 49,999
        - V1: 50,000 - 149,999
        - V2: 150,000 - 449,999
        - V3: >= 450,000
        """
        cfg = config or get_tag_config()
        v0 = cfg["vip_v0_min"]
        v1 = cfg["vip_v1_min"]
        v2 = cfg["vip_v2_min"]
        v3 = cfg["vip_v3_min"]
        if rolling_netsales < v0:
            return "Non-VIP"
        elif rolling_netsales < v1:
            return "V0"
        elif rolling_netsales < v2:
            return "V1"
        elif rolling_netsales < v3:
            return "V2"
        else:
            return "V3"

    @staticmethod
    def calculate_discount_sensitivity(
        discount_order_count: int,
        total_orders: int,
        config: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate discount sensitivity

        Returns:
            {
                "level": "High" | "Medium" | "Low",
                "ratio": discount_ratio (0-1),
                "tag": "折扣猎手" | None
            }
        """
        if total_orders == 0:
            return {"level": "Unknown", "ratio": 0, "tag": None}

        discount_ratio = discount_order_count / total_orders

        cfg = config or get_tag_config()
        if discount_ratio >= cfg["discount_high_ratio"]:
            level = "高度敏感"
            tag = "折扣猎手" if total_orders >= 3 else None
        elif discount_ratio >= cfg["discount_medium_ratio"]:
            level = "中度敏感"
            tag = None
        else:
            level = "低度敏感"
            tag = None

        return {
            "level": level,
            "ratio": round(discount_ratio * 100, 2),
            "tag": tag
        }

    @staticmethod
    def calculate_churn_risk(
        last_purchase: Optional[datetime],
        last_chat: Optional[datetime],
        config: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate churn risk (P2: thresholds from tag_config)

        Definition (thresholds configurable via tag_config):
        - Churned: No purchase in 24 months AND no chat > churn_high_days_since_chat (default 180)
        - At Risk: No purchase in 6 months AND no chat > churn_medium_days_since_chat (default 90)
        - Active: Recent activity
        """
        cfg = config or get_tag_config()
        now = datetime.now()
        has_purchase = last_purchase is not None
        has_chat = last_chat is not None

        if not has_purchase and not has_chat:
            return {"status": "Unknown", "tag": None}

        days_since_purchase = (now - last_purchase).days if has_purchase else 9999
        days_since_chat = (now - last_chat).days if has_chat else 9999

        churn_high_days = cfg["churn_high_days_since_chat"]
        churn_med_days = cfg["churn_medium_days_since_chat"]

        # Churned: 2 years no purchase AND chat > high threshold days
        if days_since_purchase > 730 and days_since_chat > churn_high_days:
            return {
                "status": "Churned",
                "tag": "流失客户",
                "days_since_purchase": days_since_purchase,
                "days_since_chat": days_since_chat
            }

        # At Risk: 6 months no purchase AND chat > medium threshold days
        if days_since_purchase > 180 and days_since_chat > churn_med_days:
            return {
                "status": "At Risk",
                "tag": "流失预警",
                "days_since_purchase": days_since_purchase,
                "days_since_chat": days_since_chat
            }

        # Active
        return {
            "status": "Active",
            "tag": None,
            "days_since_purchase": days_since_purchase,
            "days_since_chat": days_since_chat
        }

    @staticmethod
    def calculate_purchase_frequency(
        first_purchase: datetime,
        last_purchase: datetime,
        total_orders: int
    ) -> Dict[str, Any]:
        """
        Calculate purchase frequency (orders per year)
        """
        if total_orders <= 1:
            return {
                "frequency_type": "Single Purchase",
                "orders_per_year": 0,
                "tag": "一次性购买" if total_orders == 1 else "新客户"
            }

        days_span = (last_purchase - first_purchase).days
        if days_span == 0:
            days_span = 1

        orders_per_year = (total_orders / days_span) * 365

        if orders_per_year >= 6:
            frequency_type = "高频"
            tag = "高频买家"
        elif orders_per_year >= 3:
            frequency_type = "中频"
            tag = "中频买家"
        elif orders_per_year >= 1:
            frequency_type = "低频"
            tag = "低频买家"
        else:
            frequency_type = "超低频"
            tag = None

        return {
            "frequency_type": frequency_type,
            "orders_per_year": round(orders_per_year, 2),
            "tag": tag
        }

    @staticmethod
    def calculate_chat_activity(
        total_messages: int,
        first_chat: datetime,
        last_chat: datetime,
        l30d_messages: int
    ) -> Dict[str, Any]:
        """
        Calculate chat activity level
        """
        if total_messages == 0:
            return {"level": "No Chats", "tag": "沉默客户"}

        days_span = (last_chat - first_chat).days
        if days_span == 0:
            days_span = 1

        messages_per_day = total_messages / days_span

        # Recent activity
        if l30d_messages >= 20:
            recent_level = "非常活跃"
            recent_tag = "活跃买家"
        elif l30d_messages >= 5:
            recent_level = "活跃"
            recent_tag = None
        elif l30d_messages >= 1:
            recent_level = "一般"
            recent_tag = None
        else:
            recent_level = "沉寂"
            recent_tag = "沉寂客户"

        # Overall activity
        if messages_per_day >= 5:
            overall_level = "非常活跃"
        elif messages_per_day >= 1:
            overall_level = "活跃"
        elif messages_per_day >= 0.1:
            overall_level = "一般"
        else:
            overall_level = "沉默"

        return {
            "overall_level": overall_level,
            "recent_level": recent_level,
            "messages_per_day": round(messages_per_day, 2),
            "tag": recent_tag
        }

    @staticmethod
    def calculate_customer_lifecycle(
        historical_ltv: float,
        l6m_spend: float,
        l6m_orders: int,
        total_orders: int,
        is_new_customer: bool
    ) -> Dict[str, Any]:
        """
        Calculate customer lifecycle stage
        """
        tags = []

        if is_new_customer:
            if l6m_spend < 1000 and total_orders == 1:
                stage = "Potential"
                tags.append("潜力客户")
            else:
                stage = "New"
                tags.append("新客户")
        else:
            # Existing customer
            if l6m_orders >= 2 and l6m_spend > historical_ltv * 0.2:
                stage = "Growing"
                tags.append("成长客户")
            elif historical_ltv >= 10000 and total_orders >= 3:
                stage = "Mature"
                tags.append("成熟客户")
            else:
                stage = "Stable"

        # High value tag
        if historical_ltv >= 50000:
            tags.append("高价值客户")

        return {
            "stage": stage,
            "tags": tags
        }

    @staticmethod
    def calculate_lifecycle_stage(
        first_purchase_date: Optional[datetime],
        last_purchase_date: Optional[datetime],
        rolling_24m_netsales: float,
        churn_risk: str,
        config: Optional[Dict[str, float]] = None,
    ) -> str:
        """
        Calculate lifecycle stage based on precomputed table fields.
        Mirrors the SQL CASE logic in the stored procedure.

        Stages (priority order, thresholds from tag_config):
        1. 流失: last_purchase > lifecycle_churn_days_since_purchase OR churn_risk = '高'
        2. 新客: first_purchase <= lifecycle_new_customer_days
        3. 成熟: rolling_24m >= lifecycle_mature_min_netsales AND last_purchase <= 180 days
        4. 成长: first_purchase 91-365 days AND last_purchase <= 90 days AND rolling_24m < lifecycle_mature_min_netsales
        5. 预流失: fallback
        """
        cfg = config or get_tag_config()
        new_days = int(cfg["lifecycle_new_customer_days"])
        mature_min = cfg["lifecycle_mature_min_netsales"]
        churn_days = int(cfg["lifecycle_churn_days_since_purchase"])

        now = datetime.now()

        if last_purchase_date is None and first_purchase_date is None:
            return "预流失"

        days_since_last = (now - last_purchase_date).days if last_purchase_date else 9999
        days_since_first = (now - first_purchase_date).days if first_purchase_date else 9999

        # 1. 流失
        if days_since_last > churn_days or churn_risk == "高":
            return "流失"

        # 2. 新客
        if days_since_first <= new_days:
            return "新客"

        # 3. 成熟
        if rolling_24m_netsales >= mature_min and days_since_last <= 180:
            return "成熟"

        # 4. 成长
        if 91 <= days_since_first <= 365 and days_since_last <= 90 and rolling_24m_netsales < mature_min:
            return "成长"

        # 5. 预流失 (fallback)
        return "预流失"

    @staticmethod
    def determine_category_preference(
        category_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Determine category preference from category stats

        category_data: [
            {"category": "PIPES", "category_orders": 10, "category_spend": 5000},
            ...
        ]
        """
        if not category_data:
            return {"top_category": "Unknown", "tags": []}

        total_orders = sum(item["category_orders"] for item in category_data)
        total_spend = sum(item["category_spend"] for item in category_data)

        # Sort by orders
        sorted_categories = sorted(category_data, key=lambda x: x["category_orders"], reverse=True)
        top_category = sorted_categories[0]["category"]
        top_ratio = sorted_categories[0]["category_orders"] / total_orders if total_orders > 0 else 0

        tags = []
        category_mapping = {
            "PIPES": "斗客",
            "ACCESSORIES": "配件客",
            "BELTS": "皮带爱好者",
            "WOVEN OUTERWEAR": "成衣客"
        }

        if top_category in category_mapping and top_ratio >= 0.5:
            tags.append(category_mapping[top_category])

        # Balanced if no category dominates
        if top_ratio < 0.4 and len(category_data) >= 3:
            tags.append("全能型买家")

        return {
            "top_category": top_category,
            "top_ratio": round(top_ratio * 100, 2),
            "tags": tags
        }

    @staticmethod
    def calculate_high_value_tags(
        historical_ltv: float,
        l6m_spend: float,
        order_history: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Calculate high value related tags
        """
        tags = []

        # Big spender
        if historical_ltv >= 50000:
            tags.append("大额客户")

        # L6M high value
        if l6m_spend >= 5000:
            tags.append("近期高消费")

        # Check for large single order
        for order in order_history:
            if order.get("net_amount", 0) >= 10000:
                tags.append("大单客户")
                break

        return tags

    @staticmethod
    def calculate_city_tier(city: str) -> str:
        """
        Classify city into tiers
        """
        if not city:
            return "Unknown"

        tier1 = ["北京", "上海", "广州", "深圳", "Beijing", "Shanghai", "Guangzhou", "Shenzhen"]
        tier1_5 = ["成都", "杭州", "重庆", "武汉", "西安", "苏州", "天津", "南京",
                   "Chengdu", "Hangzhou", "Chongqing", "Wuhan", "Xi'an", "Suzhou", "Tianjin", "Nanjing"]

        if city in tier1:
            return "一线城市"
        elif city in tier1_5:
            return "新一线"
        else:
            return "其他城市"

    # ============================================
    # RFM Customer Classification Methods
    # ============================================

    @staticmethod
    def calculate_rfm_scores(
        last_purchase_date: Optional[datetime],
        total_orders: int,
        historical_net_sales: float,
        chat_frequency_days: int = 0
    ) -> Dict[str, int]:
        """
        Calculate RFM scores for a buyer

        RFM Model (Luxury E-commerce Optimized):
        - R (Recency): How recently did they purchase?
        - F (Frequency): How often do they purchase?
        - M (Monetary): How much do they spend?

        Luxury thresholds (dunhill specific - lower frequency, higher value):
        - R: ≤60d=5, 61-180d=4, 181-365d=3, 366-730d=2, >730d=1
        - F: ≥5单=5, 3-4单=4, 2单=3, 1单+聊天=2, 1单无聊天=1
        - M: ≥50K=5, 20K-50K=4, 10K-20K=3, 5K-10K=2, <5K=1

        Returns:
            {
                "r_score": int (1-5),
                "f_score": int (1-5),
                "m_score": int (1-5)
            }
        """
        now = datetime.now()

        # Calculate R Score (Recency)
        if last_purchase_date is None:
            r_score = 0
        else:
            days_since_purchase = (now - last_purchase_date).days
            if days_since_purchase <= 60:
                r_score = 5
            elif days_since_purchase <= 180:
                r_score = 4
            elif days_since_purchase <= 365:
                r_score = 3
            elif days_since_purchase <= 730:
                r_score = 2
            else:
                r_score = 1

        # Calculate F Score (Frequency)
        if total_orders >= 5:
            f_score = 5
        elif total_orders >= 3:
            f_score = 4
        elif total_orders == 2:
            f_score = 3
        elif total_orders == 1 and chat_frequency_days > 0:
            f_score = 2
        elif total_orders == 1:
            f_score = 1
        else:
            f_score = 0

        # Calculate M Score (Monetary)
        if historical_net_sales >= 50000:
            m_score = 5
        elif historical_net_sales >= 20000:
            m_score = 4
        elif historical_net_sales >= 10000:
            m_score = 3
        elif historical_net_sales >= 5000:
            m_score = 2
        else:
            m_score = 1

        return {
            "r_score": r_score,
            "f_score": f_score,
            "m_score": m_score
        }

    @staticmethod
    def determine_rfm_segment(r_score: int, f_score: int, m_score: int) -> Dict[str, Any]:
        """
        Determine customer segment based on RFM scores
        Simplified Version - 11 Categories
        覆盖所有 125 combinations
        """
        segment = "待分类"
        strategy = ""
        priority = "中"

        # M=5 (>=50K) - 核心VIP
        if m_score == 5:
            if r_score >= 4 and f_score >= 4:
                segment = "重要价值客户"
                strategy = "VIP专属服务，新品优先"
                priority = "紧急"
            elif r_score >= 4:
                segment = "重要发展客户"
                strategy = "提升复购频次"
                priority = "高"
            elif f_score >= 4:
                segment = "重要保持客户"
                strategy = "召回维护"
                priority = "紧急"
            else:
                segment = "重要挽留客户"
                strategy = "紧急挽回"
                priority = "紧急"

        # M=4 (20K-50K) - 高价值
        elif m_score == 4:
            if r_score >= 4 and f_score >= 4:
                segment = "优质活跃客户"
                strategy = "重点培养，升级VIP"
                priority = "高"
            elif r_score >= 4 and f_score == 3:
                segment = "优质发展客户"
                strategy = "有升级潜力"
                priority = "高"
            elif r_score >= 4:
                segment = "优质新客"
                strategy = "新发展优质客户"
                priority = "高"
            elif f_score >= 3:
                segment = "优质保持客户"
                strategy = "持续维护"
                priority = "高"
            else:
                segment = "优质挽留客户"
                strategy = "激活召回"
                priority = "高"

        # M=3 (10K-20K) - 中等价值
        elif m_score == 3:
            if r_score >= 4 and f_score >= 4:
                segment = "成长活跃客户"
                strategy = "成长性好，升级潜力"
                priority = "中"
            elif r_score >= 4 and f_score == 3:
                segment = "成长发展客户"
                strategy = "有潜力，推荐升级"
                priority = "中"
            elif r_score >= 4:
                segment = "成长新客"
                strategy = "新客户，首次复购激励"
                priority = "中"
            elif f_score >= 3:
                segment = "成长保持客户"
                strategy = "维护关系，定期触达"
                priority = "中"
            else:
                segment = "成长挽留客户"
                strategy = "激活活动，促销触达"
                priority = "中"

        # M=2 (5K-10K) - 潜力
        elif m_score == 2:
            if r_score >= 4:
                segment = "潜力客户"
                strategy = "引导升级，推荐高客单"
                priority = "中"
            else:
                segment = "待激活客户"
                strategy = "促销激活，限时优惠"
                priority = "低"

        # M=1 (<5K) - 入门
        elif m_score == 1:
            if r_score >= 4:
                segment = "新客户"
                strategy = "培育转化，面向引导"
                priority = "中"
            else:
                segment = "低价值客户"
                strategy = "低优先级，批量触达"
                priority = "低"

        # 特殊情况
        if r_score == 1:
            segment = "已流失"
            strategy = "批量触达，大促唤醒"
            priority = "低"
        elif r_score == 0:
            segment = "无购买记录"
            strategy = "数据异常，需核实"
            priority = "低"

        return {
            "segment": segment,
            "strategy": strategy,
            "priority": priority
        }

    @staticmethod
    def calculate_follow_priority(
        rfm_segment: str,
        churn_risk: str,
        l6m_netsales: float,
        vip_level: str
    ) -> str:
        """
        Calculate follow-up priority based on multiple factors

        Priority levels: 紧急/高/中/低

        Factors:
        - RFM segment
        - Churn risk
        - Recent spending (L6M)
        - VIP level
        """
        # Start with RFM segment priority
        priority_map = {
            "重要价值客户": "紧急",
            "重要发展客户": "高",
            "重要保持客户": "高",
            "一般客户": "中",
            "潜力客户": "中",
            "流失预警": "紧急",
            "已流失": "低"
        }

        priority = priority_map.get(rfm_segment, "中")

        # Upgrade priority based on additional factors
        if churn_risk == "高" and priority in ["中", "低"]:
            priority = "高"

        if vip_level in ["V3", "V2"] and priority != "紧急":
            priority = "高" if priority == "中" else priority

        if l6m_netsales >= 10000 and priority == "低":
            priority = "中"

        return priority

    @staticmethod
    def calculate_complaint_tendency(
        refund_rate: float,
        chat_frequency_days: int,
        sentiment_score: Optional[float] = None
    ) -> str:
        """
        Calculate complaint tendency based on refund rate and chat behavior

        Returns: 高/中/低
        """
        # High refund rate indicates potential complaint tendency
        if refund_rate >= 0.15:
            return "高"
        elif refund_rate >= 0.08:
            return "中"

        # High chat frequency without purchase may indicate issues
        if chat_frequency_days > 10 and sentiment_score and sentiment_score < 0.4:
            return "高"

        # If we have sentiment score, use it
        if sentiment_score is not None:
            if sentiment_score < 0.3:
                return "高"
            elif sentiment_score < 0.5:
                return "中"

        return "低"

    @staticmethod
    def calculate_intent_scores(intent_distribution: Dict[str, int]) -> Dict[str, int]:
        """
        Calculate pre-sale and post-sale scores from intent distribution

        Args:
            intent_distribution: {
                "Pre-sale Inquiry": int,
                "Post-sale Support": int,
                "Logistics": int,
                "Usage Guide": int,
                "Complaint": int
            }

        Returns:
            {
                "pre_sale_score": int (0-100),
                "post_sale_score": int (0-100),
                "dominant_intent": str
            }
        """
        total = sum(intent_distribution.values()) or 1

        # Pre-sale score: Pre-sale Inquiry占比
        pre_sale_count = intent_distribution.get("Pre-sale Inquiry", 0)
        pre_sale_score = min(100, int((pre_sale_count / total) * 100))

        # Post-sale score: Post-sale Support + Complaint + Usage Guide
        post_sale_count = (
            intent_distribution.get("Post-sale Support", 0) +
            intent_distribution.get("Complaint", 0) +
            intent_distribution.get("Usage Guide", 0)
        )
        post_sale_score = min(100, int((post_sale_count / total) * 100))

        # Determine dominant intent
        if intent_distribution:
            dominant_intent = max(intent_distribution.items(), key=lambda x: x[1])[0]
        else:
            dominant_intent = "Unknown"

        return {
            "pre_sale_score": pre_sale_score,
            "post_sale_score": post_sale_score,
            "dominant_intent": dominant_intent
        }
