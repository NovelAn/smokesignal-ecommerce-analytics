"""
Tag calculation logic for buyer segmentation
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


class TagCalculator:
    """Calculate buyer tags based on order and chat data"""

    @staticmethod
    def calculate_vip_level(rolling_netsales: float) -> str:
        """
        Calculate VIP level based on rolling 24 months netsales

        VIP Levels:
        - Non-VIP: < 30,000
        - V0: 30,000 - 49,999
        - V1: 50,000 - 149,999
        - V2: 150,000 - 449,999
        - V3: >= 450,000
        """
        if rolling_netsales < 30000:
            return "Non-VIP"
        elif rolling_netsales < 50000:
            return "V0"
        elif rolling_netsales < 150000:
            return "V1"
        elif rolling_netsales < 450000:
            return "V2"
        else:
            return "V3"

    @staticmethod
    def calculate_discount_sensitivity(
        discount_order_count: int,
        total_orders: int
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

        if discount_ratio >= 0.7:
            level = "高度敏感"
            tag = "折扣猎手" if total_orders >= 3 else None
        elif discount_ratio >= 0.4:
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
        last_chat: Optional[datetime]
    ) -> Dict[str, Any]:
        """
        Calculate churn risk

        Definition:
        - Churned: No purchase in 24 months AND no chat in 6 months
        - At Risk: Warning signs
        - Active: Recent activity
        """
        now = datetime.now()
        has_purchase = last_purchase is not None
        has_chat = last_chat is not None

        if not has_purchase and not has_chat:
            return {"status": "Unknown", "tag": None}

        days_since_purchase = (now - last_purchase).days if has_purchase else 9999
        days_since_chat = (now - last_chat).days if has_chat else 9999

        # Churned: 2 years no purchase AND 6 months no chat
        if days_since_purchase > 730 and days_since_chat > 180:
            return {
                "status": "Churned",
                "tag": "流失客户",
                "days_since_purchase": days_since_purchase,
                "days_since_chat": days_since_chat
            }

        # At Risk: 6 months no purchase AND 30 days no chat
        if days_since_purchase > 180 and days_since_chat > 30:
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
