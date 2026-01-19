"""
Buyer profile analyzer - Main analysis engine
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
from backend.database import Database, BuyerQueries
from backend.database.cache import buyer_list_cache
from backend.analytics.tag_calculator import TagCalculator


class BuyerAnalyzer:
    """Main buyer profile analyzer"""

    def __init__(self):
        from backend.config import settings
        db_name = settings.db_name_to_use if settings.db_name_to_use else None
        self.db = Database(db_name=db_name)
        self.tag_calculator = TagCalculator()

    def get_all_buyers(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get list of buyer nicknames with filtering, search and pagination

        Args:
            start_date: Filter by orders after this date (YYYY-MM-DD)
            end_date: Filter by orders before this date (YYYY-MM-DD)
            search: Search by nickname (partial match)
            limit: Max number of results
            offset: Pagination offset
            use_cache: Whether to use cache (default: True)
        """
        # Check cache first
        if use_cache:
            cache_key = {
                "start_date": start_date,
                "end_date": end_date,
                "search": search,
                "limit": limit,
                "offset": offset
            }
            cached = buyer_list_cache.get(**cache_key)
            if cached:
                print("📦 Cache hit!")
                return cached

        # Query database
        query, params = BuyerQueries.get_all_buyers(start_date, end_date, search, limit, offset)
        results = self.db.execute_query(query, params)

        # Get total count for pagination (only for first page)
        total = None
        if offset == 0:
            count_query, count_params = BuyerQueries.get_buyers_count(start_date, end_date, search)
            count_result = self.db.execute_query(count_query, count_params)
            total = count_result[0]["total"] if count_result else 0

        result = {
            "buyers": [r["user_nick"] for r in results],
            "total": total,
            "limit": limit,
            "offset": offset
        }

        # Cache the result
        if use_cache and total is not None:
            buyer_list_cache.set(result, **cache_key)
            print("💾 Cached result")

        return result

    def analyze_buyer(self, user_nick: str) -> Dict[str, Any]:
        """
        Complete buyer analysis

        Returns comprehensive buyer profile with tags, metrics, and order history
        """
        # Fetch data from database
        basic_metrics = self._fetch_basic_metrics(user_nick)
        rolling_metrics = self._fetch_rolling_metrics(user_nick)
        l6m_metrics = self._fetch_l6m_metrics(user_nick)
        chat_metrics = self._fetch_chat_metrics(user_nick)
        l30d_chats = self._fetch_l30d_chats(user_nick)
        category_data = self._fetch_category_data(user_nick)
        order_history = self._fetch_order_history(user_nick)

        # Calculate all tags
        tags = self._calculate_all_tags(
            basic_metrics,
            rolling_metrics,
            l6m_metrics,
            chat_metrics,
            l30d_chats,
            category_data,
            order_history
        )

        # Build profile
        profile = self._build_profile(
            basic_metrics,
            rolling_metrics,
            l6m_metrics,
            chat_metrics,
            category_data,
            tags
        )

        return {
            "user_nick": user_nick,
            "profile": profile,
            "order_history": order_history,
            "chat_metrics": chat_metrics,
            "tags": tags["all_tags"]
        }

    def _fetch_basic_metrics(self, user_nick: str) -> Optional[Dict[str, Any]]:
        """Fetch basic buyer metrics from orders"""
        query = BuyerQueries.get_buyer_basic_metrics() + " AND 买家昵称 = %s"
        results = self.db.execute_query(query, (user_nick,))
        return results[0] if results else None

    def _fetch_rolling_metrics(self, user_nick: str) -> Optional[Dict[str, Any]]:
        """Fetch 24-month rolling metrics"""
        query, params = BuyerQueries.get_buyer_rolling_metrics(24)
        query += " HAVING user_nick = %s"
        params += (user_nick,)
        results = self.db.execute_query(query, params)
        return results[0] if results else None

    def _fetch_l6m_metrics(self, user_nick: str) -> Optional[Dict[str, Any]]:
        """Fetch last 6 months metrics"""
        query = BuyerQueries.get_buyer_l6m_metrics() + " HAVING user_nick = %s"
        results = self.db.execute_query(query, (user_nick,))
        return results[0] if results else None

    def _fetch_chat_metrics(self, user_nick: str) -> Optional[Dict[str, Any]]:
        """Fetch chat summary metrics"""
        query = BuyerQueries.get_chat_summary_metrics() + " HAVING user_nick = %s"
        results = self.db.execute_query(query, (user_nick,))
        return results[0] if results else None

    def _fetch_l30d_chats(self, user_nick: str) -> Optional[Dict[str, Any]]:
        """Fetch last 30 days chat metrics"""
        query = BuyerQueries.get_buyer_l30d_chats() + " HAVING user_nick = %s"
        results = self.db.execute_query(query, (user_nick,))
        return results[0] if results else None

    def _fetch_category_data(self, user_nick: str) -> List[Dict[str, Any]]:
        """Fetch category preference data"""
        query = BuyerQueries.get_buyer_category_preference() + " AND 买家昵称 = %s"
        return self.db.execute_query(query, (user_nick,))

    def _fetch_order_history(self, user_nick: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch order history"""
        query, params = BuyerQueries.get_buyer_order_history(user_nick, limit)
        return self.db.execute_query(query, params)

    def _calculate_all_tags(
        self,
        basic_metrics: Optional[Dict],
        rolling_metrics: Optional[Dict],
        l6m_metrics: Optional[Dict],
        chat_metrics: Optional[Dict],
        l30d_chats: Optional[Dict],
        category_data: List[Dict],
        order_history: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate all tags and return organized result"""
        all_tags = []
        tag_details = {}

        # VIP Level (from rolling 24-month data)
        rolling_netsales = rolling_metrics.get("rolling_netsales", 0) if rolling_metrics else 0
        vip_level = self.tag_calculator.calculate_vip_level(rolling_netsales)
        all_tags.append(vip_level)
        tag_details["vip_level"] = vip_level
        tag_details["rolling_netsales"] = rolling_netsales

        # Discount Sensitivity
        if basic_metrics and basic_metrics.get("total_orders", 0) > 0:
            discount_info = self.tag_calculator.calculate_discount_sensitivity(
                basic_metrics.get("discount_order_count", 0),
                basic_metrics.get("total_orders", 0)
            )
            all_tags.append(discount_info["level"])
            if discount_info["tag"]:
                all_tags.append(discount_info["tag"])
            tag_details["discount_sensitivity"] = discount_info

        # Churn Risk
        last_purchase = basic_metrics.get("last_purchase_date") if basic_metrics else None
        last_chat = chat_metrics.get("last_chat_date") if chat_metrics else None
        churn_info = self.tag_calculator.calculate_churn_risk(last_purchase, last_chat)
        if churn_info["tag"]:
            all_tags.append(churn_info["tag"])
        tag_details["churn_risk"] = churn_info

        # Purchase Frequency
        if basic_metrics and basic_metrics.get("total_orders", 0) > 1:
            freq_info = self.tag_calculator.calculate_purchase_frequency(
                basic_metrics.get("first_purchase_date"),
                basic_metrics.get("last_purchase_date"),
                basic_metrics.get("total_orders", 0)
            )
            if freq_info["tag"]:
                all_tags.append(freq_info["tag"])
            tag_details["purchase_frequency"] = freq_info

        # Chat Activity
        if chat_metrics:
            chat_activity = self.tag_calculator.calculate_chat_activity(
                chat_metrics.get("total_messages", 0),
                chat_metrics.get("first_chat_date"),
                chat_metrics.get("last_chat_date"),
                l30d_chats.get("l30d_message_count", 0) if l30d_chats else 0
            )
            if chat_activity["tag"]:
                all_tags.append(chat_activity["tag"])
            tag_details["chat_activity"] = chat_activity

        # Customer Lifecycle
        if basic_metrics:
            lifecycle = self.tag_calculator.calculate_customer_lifecycle(
                basic_metrics.get("historical_ltv", 0),
                l6m_metrics.get("l6m_spend", 0) if l6m_metrics else 0,
                l6m_metrics.get("l6m_orders", 0) if l6m_metrics else 0,
                basic_metrics.get("total_orders", 0),
                basic_metrics.get("customer_type", "") == "新客户"
            )
            all_tags.extend(lifecycle["tags"])
            tag_details["lifecycle"] = lifecycle

        # Category Preference
        if category_data:
            category_pref = self.tag_calculator.determine_category_preference(category_data)
            all_tags.extend(category_pref["tags"])
            tag_details["category_preference"] = category_pref

        # High Value Tags
        if basic_metrics:
            high_value_tags = self.tag_calculator.calculate_high_value_tags(
                basic_metrics.get("historical_ltv", 0),
                l6m_metrics.get("l6m_spend", 0) if l6m_metrics else 0,
                order_history
            )
            all_tags.extend(high_value_tags)

        # City Tier
        if basic_metrics and basic_metrics.get("city"):
            city_tier = self.tag_calculator.calculate_city_tier(basic_metrics["city"])
            tag_details["city_tier"] = city_tier

        # Remove duplicates and None
        all_tags = list(set([tag for tag in all_tags if tag]))

        return {
            "all_tags": all_tags,
            "details": tag_details
        }

    def _build_profile(
        self,
        basic_metrics: Optional[Dict],
        rolling_metrics: Optional[Dict],
        l6m_metrics: Optional[Dict],
        chat_metrics: Optional[Dict],
        category_data: List[Dict],
        tags: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build buyer profile object"""
        if not basic_metrics:
            return self._empty_profile()

        profile = {
            # Basic info
            "user_nick": basic_metrics.get("user_nick"),
            "city": basic_metrics.get("city", "Unknown"),
            "is_new_customer": basic_metrics.get("customer_type", "") == "新客户",

            # Historical metrics
            "historical_ltv": float(basic_metrics.get("historical_ltv", 0)),
            "total_orders": int(basic_metrics.get("total_orders", 0)),
            "discount_ratio": tags["details"].get("discount_sensitivity", {}).get("ratio", 0),

            # L6M metrics
            "l6m_spend": float(l6m_metrics.get("l6m_spend", 0)) if l6m_metrics else 0,
            "l6m_frequency": int(l6m_metrics.get("l6m_orders", 0)) if l6m_metrics else 0,

            # VIP
            "vip_level": tags["details"].get("vip_level", "Non-VIP"),
            "rolling_netsales": tags["details"].get("rolling_netsales", 0),

            # Engagement
            "recent_chat_frequency": int(chat_metrics.get("total_messages", 0)) if chat_metrics else 0,
            "avg_reply_interval_days": 0,  # TODO: Calculate from chat messages
            "last_interaction_date": str(chat_metrics.get("last_chat_date")) if chat_metrics else None,

            # Tags
            "tags": tags["all_tags"],

            # Category preference
            "top_category": tags["details"].get("category_preference", {}).get("top_category", "Unknown"),

            # Placeholder for AI analysis
            "analysis": {
                "summary": "",
                "key_interests": [],
                "pain_points": [],
                "recommended_action": ""
            },

            # Placeholder for intent scores
            "intent_scores": []
        }

        return profile

    def _empty_profile(self) -> Dict[str, Any]:
        """Return empty profile for buyer with no data"""
        return {
            "user_nick": "Unknown",
            "city": "Unknown",
            "is_new_customer": True,
            "historical_ltv": 0,
            "total_orders": 0,
            "discount_ratio": 0,
            "l6m_spend": 0,
            "l6m_frequency": 0,
            "vip_level": "Non-VIP",
            "rolling_netsales": 0,
            "recent_chat_frequency": 0,
            "avg_reply_interval_days": 0,
            "last_interaction_date": None,
            "tags": [],
            "top_category": "Unknown",
            "analysis": {
                "summary": "暂无数据",
                "key_interests": [],
                "pain_points": [],
                "recommended_action": ""
            },
            "intent_scores": []
        }

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics for dashboard overview"""
        # Get all buyers basic metrics
        all_metrics = self.db.execute_query(BuyerQueries.get_buyer_basic_metrics())

        if not all_metrics:
            return self._empty_dashboard_metrics()

        total_buyers = len(all_metrics)
        total_ltv = sum(m.get("historical_ltv", 0) for m in all_metrics)
        total_orders = sum(m.get("total_orders", 0) for m in all_metrics)

        # Calculate VIP distribution
        vip_distribution = {"Non-VIP": 0, "V0": 0, "V1": 0, "V2": 0, "V3": 0}
        for m in all_metrics:
            # Need rolling metrics for accurate VIP, using historical as approximation
            vip_level = self.tag_calculator.calculate_vip_level(m.get("historical_ltv", 0))
            vip_distribution[vip_level] += 1

        # Get chat metrics
        all_chat_metrics = self.db.execute_query(BuyerQueries.get_chat_summary_metrics())
        total_chats = sum(c.get("total_messages", 0) for c in all_chat_metrics) if all_chat_metrics else 0

        return {
            "total_buyers": total_buyers,
            "total_ltv": total_ltv,
            "total_orders": total_orders,
            "total_chats": total_chats,
            "avg_ltv": total_ltv / total_buyers if total_buyers > 0 else 0,
            "vip_distribution": vip_distribution
        }

    def _empty_dashboard_metrics(self) -> Dict[str, Any]:
        """Return empty dashboard metrics"""
        return {
            "total_buyers": 0,
            "total_ltv": 0,
            "total_orders": 0,
            "total_chats": 0,
            "avg_ltv": 0,
            "vip_distribution": {"Non-VIP": 0, "V0": 0, "V1": 0, "V2": 0, "V3": 0}
        }
