"""
SQL queries for buyer analytics
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


class BuyerQueries:
    """SQL queries for buyer data aggregation"""

    @staticmethod
    def get_buyer_basic_metrics() -> str:
        """
        Get basic buyer metrics from order data
        Aggregates: total_orders, historical_ltv, first/last purchase, discount metrics
        """
        return """
        SELECT
            买家昵称 as user_nick,
            COUNT(DISTINCT 订单号) as total_orders,
            SUM(成交总金额 - IFNULL(退款金额, 0)) as historical_ltv,
            SUM(成交总金额) as total_gmv,
            SUM(IFNULL(退款金额, 0)) as total_refund_amount,
            MIN(最后付款时间) as first_purchase_date,
            MAX(最后付款时间) as last_purchase_date,
            SUM(CASE WHEN FP_MD = 'MD' THEN 1 ELSE 0 END) as discount_order_count,
            SUM(CASE WHEN FP_MD = 'FP' THEN 1 ELSE 0 END) as fullprice_order_count,
            SUM(CASE WHEN FP_MD = 'MD' THEN (成交总金额 - IFNULL(退款金额, 0)) ELSE 0 END) as discount_spend_amount,
            MAX(城市) as city,
            MAX(client_monthly_tag) as customer_type
        FROM dunhill_t01_trade_line
        WHERE 最后付款时间 IS NOT NULL
        GROUP BY 买家昵称
        """

    @staticmethod
    def get_buyer_rolling_metrics(months: int = 24) -> str:
        """
        Get rolling window metrics (default: 24 months for VIP calculation)
        """
        return f"""
        SELECT
            买家昵称 as user_nick,
            COUNT(DISTINCT 订单号) as rolling_orders,
            SUM(成交总金额 - IFNULL(退款金额, 0)) as rolling_netsales,
            MIN(最后付款时间) as rolling_first_purchase,
            MAX(最后付款时间) as rolling_last_purchase
        FROM dunhill_t01_trade_line
        WHERE 最后付款时间 >= DATE_SUB(NOW(), INTERVAL {months} MONTH)
        GROUP BY 买家昵称
        """

    @staticmethod
    def get_buyer_l6m_metrics() -> str:
        """
        Get Last 6 Months metrics
        """
        return """
        SELECT
            买家昵称 as user_nick,
            COUNT(DISTINCT 订单号) as l6m_orders,
            SUM(成交总金额 - IFNULL(退款金额, 0)) as l6m_spend,
            MAX(最后付款时间) as l6m_last_purchase
        FROM dunhill_t01_trade_line
        WHERE 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
        GROUP BY 买家昵称
        """

    @staticmethod
    def get_buyer_category_preference() -> str:
        """
        Get category preference by buyer
        """
        return """
        SELECT
            买家昵称 as user_nick,
            category,
            COUNT(DISTINCT 订单号) as category_orders,
            SUM(成交总金额 - IFNULL(退款金额, 0)) as category_spend,
            COUNT(DISTINCT 天猫外部编码) as unique_skus
        FROM dunhill_t01_trade_line
        WHERE category IS NOT NULL AND category != ''
        GROUP BY 买家昵称, category
        ORDER BY 买家昵称, category_orders DESC
        """

    @staticmethod
    def get_buyer_order_history(user_nick: str, limit: int = 50) -> str:
        """
        Get detailed order history for a specific buyer
        """
        return f"""
        SELECT
            订单号 as order_id,
            子订单号 as sub_order_id,
            最后付款时间 as purchase_date,
            成交总金额 as gmv,
            IFNULL(退款金额, 0) as refund_amount,
            (成交总金额 - IFNULL(退款金额, 0)) as net_amount,
            FP_MD as price_type,
            category,
            product_name,
            天猫外部编码 as sku,
            城市 as city
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 = %s
        ORDER BY 最后付款时间 DESC
        LIMIT {limit}
        """

    @staticmethod
    def get_chat_summary_metrics() -> str:
        """
        Get chat activity summary by buyer
        """
        return """
        SELECT
            user_nick,
            COUNT(*) as total_messages,
            MIN(msg_time) as first_chat_date,
            MAX(msg_time) as last_chat_date,
            COUNT(DISTINCT DATE(msg_time)) as chat_days,
            COUNT(DISTINCT DATE(msg_time)) / DATEDIFF(MAX(msg_time), MIN(msg_time)) * 30 as monthly_chat_frequency
        FROM chat_history
        WHERE msg_time IS NOT NULL
        GROUP BY user_nick
        """

    @staticmethod
    def get_buyer_l30d_chats() -> str:
        """
        Get Last 30 Days chat metrics
        """
        return """
        SELECT
            user_nick,
            COUNT(*) as l30d_message_count,
            MAX(msg_time) as l30d_last_chat
        FROM chat_history
        WHERE msg_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        GROUP BY user_nick
        """

    @staticmethod
    def get_chat_messages(user_nick: str, limit: int = 100) -> str:
        """
        Get chat messages for a specific buyer
        """
        return f"""
        SELECT
            id,
            user_nick,
            sender_nick,
            msg_time,
            msg_type,
            content
        FROM chat_history
        WHERE user_nick = %s
        ORDER BY msg_time DESC
        LIMIT {limit}
        """

    @staticmethod
    def get_all_buyers(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> str:
        """
        Get list of unique buyers from summary table (optimized)
        Uses buyer_summary table instead of complex view for better performance

        Args:
            start_date: Filter orders after this date
            end_date: Filter orders before this date
            search: Search by nickname (partial match)
            limit: Max results
            offset: Pagination offset
        """
        where_clauses = []

        if start_date:
            where_clauses.append(f"last_order_date >= '{start_date}'")

        if end_date:
            where_clauses.append(f"last_order_date <= '{end_date}'")

        if search:
            where_clauses.append(f"buyer_nick LIKE '%{search}%'")

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        return f"""
        SELECT buyer_nick as user_nick
        FROM buyer_summary
        {where_sql}
        ORDER BY last_order_date DESC
        LIMIT {limit}
        OFFSET {offset}
        """

    @staticmethod
    def get_buyers_count(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        search: Optional[str] = None
    ) -> str:
        """Get total count of unique buyers from summary table (ultra fast)"""
        where_clauses = []

        if start_date:
            where_clauses.append(f"last_order_date >= '{start_date}'")

        if end_date:
            where_clauses.append(f"last_order_date <= '{end_date}'")

        if search:
            where_clauses.append(f"buyer_nick LIKE '%{search}%'")

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        return f"""
        SELECT COUNT(*) as total
        FROM buyer_summary
        {where_sql}
        """

    @staticmethod
    def get_daily_stats(days: int = 30) -> str:
        """
        Get daily statistics for dashboard
        """
        return f"""
        SELECT
            DATE(msg_time) as date,
            COUNT(DISTINCT user_nick) as unique_buyers,
            COUNT(*) as total_chats,
            COUNT(DISTINCT CASE WHEN sender_nick != user_nick THEN user_nick END) as conversations
        FROM chat_history
        WHERE msg_time >= DATE_SUB(NOW(), INTERVAL {days} DAY)
        GROUP BY DATE(msg_time)
        ORDER BY date DESC
        """

    @staticmethod
    def get_actionable_customers() -> str:
        """
        Get actionable customers (priority board)
        Combines churn risk, high value, etc.
        """
        return """
        WITH buyer_metrics AS (
            SELECT
                买家昵称 as user_nick,
                MAX(最后付款时间) as last_purchase,
                MAX(城市) as city,
                SUM(成交总金额 - IFNULL(退款金额, 0)) as total_ltv
            FROM dunhill_t01_trade_line
            WHERE 买家昵称 IS NOT NULL AND 买家昵称 != ''
            GROUP BY 买家昵称
        ),
        chat_metrics AS (
            SELECT
                user_nick,
                MAX(msg_time) as last_chat
            FROM chat_history
            GROUP BY user_nick
        )
        SELECT
            COALESCE(bm.user_nick, cm.user_nick) as user_nick,
            bm.last_purchase,
            cm.last_chat,
            bm.city,
            COALESCE(bm.total_ltv, 0) as total_ltv
        FROM buyer_metrics bm
        LEFT JOIN chat_metrics cm ON bm.user_nick = cm.user_nick
        LIMIT 100
        """
