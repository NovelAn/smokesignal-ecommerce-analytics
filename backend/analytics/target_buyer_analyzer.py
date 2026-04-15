"""
目标买家分析器(优化版)
使用预计算表实现超快速查询
"""
from typing import Dict, List, Any, Optional
from backend.database import Database
from backend.database.target_buyer_queries import TargetBuyerQueries


class TargetBuyerAnalyzer:
    """
    目标买家分析器(优化版)

    使用预计算表实现超快速查询,性能提升10-50倍

    使用方式:
        analyzer = TargetBuyerAnalyzer()
        buyers = analyzer.get_all_buyers(limit=100)
        metrics = analyzer.get_dashboard_metrics()
    """

    def __init__(self):
        """
        初始化分析器
        """
        from backend.config import settings
        # 优先使用配置的数据库,否则默认使用aliyunDB
        db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
        self.db = Database(db_name=db_name)
        self.queries = TargetBuyerQueries(self.db)

    def get_all_buyers(
        self,
        search: Optional[str] = None,
        buyer_type: Optional[Any] = None,
        vip_level: Optional[Any] = None,
        channel: Optional[Any] = None,
        last_purchase_after: Optional[str] = None,
        chat_status: Optional[str] = None,
        sort_by: str = 'last_purchase',
        limit: int = 100,
        offset: int = 0,
        include_total: bool = False
    ) -> Dict[str, Any]:
        """
        获取所有目标买家列表(超快!)

        性能: < 0.5秒 (从VIEW查询需要10-30秒)

        Args:
            search: 昵称模糊搜索
            buyer_type: 买家类型筛选 (SMOKER/VIC/BOTH) 或 列表
            vip_level: VIP等级筛选 (V3/V2/V1/V0/Non-VIP) 或 列表
            channel: 渠道筛选 (DTC/PFS) 或 列表
            last_purchase_after: 最后购买日期筛选 (YYYY-MM-DD)
            chat_status: 聊天状态筛选 ('chatted'/'no_chat')
            sort_by: 排序字段 (last_purchase/l6m_netsales/vip_level)
            limit: 返回数量
            offset: 偏移量

        Returns:
            买家列表 + 总数(用于分页)
        """
        # 查询买家列表
        buyers = self.queries.get_all_target_buyers(
            search=search,
            buyer_type=buyer_type,
            vip_level=vip_level,
            channel=channel,
            last_purchase_after=last_purchase_after,
            chat_status=chat_status,
            sort_by=sort_by,
            limit=limit,
            offset=offset
        )

        # 获取总数(可选,大数据量场景可能较慢)
        total = None
        if include_total and offset == 0:
            total = self.queries.get_target_buyers_count(
                buyer_type=buyer_type,
                vip_level=vip_level,
                channel=channel,
                last_purchase_after=last_purchase_after,
                chat_status=chat_status
            )

        return {
            "buyers": buyers,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    def get_buyer_profile(self, buyer_nick: str) -> Optional[Dict[str, Any]]:
        """
        获取买家360°详情(超快!)

        性能: < 0.1秒 (主键查询)

        Args:
            buyer_nick: 买家昵称

        Returns:
            买家详细信息,如果不存在返回None
        """
        return self.queries.get_target_buyer_by_nick(buyer_nick)

    def get_buyers_count(
        self,
        buyer_type: Optional[Any] = None,
        vip_level: Optional[Any] = None,
        channel: Optional[Any] = None,
        last_purchase_after: Optional[str] = None,
        chat_status: Optional[str] = None
    ) -> int:
        return self.queries.get_target_buyers_count(
            buyer_type=buyer_type,
            vip_level=vip_level,
            channel=channel,
            last_purchase_after=last_purchase_after,
            chat_status=chat_status
        )

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """
        获取Dashboard汇总指标(超快!)

        性能: < 0.1秒 (直接聚合预计算表)

        Returns:
            包含所有指标的字典
        """
        return self.queries.get_dashboard_metrics()

    def get_buyers_by_type(
        self,
        buyer_type: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        按买家类型筛选

        性能: < 0.1秒 (使用索引)

        Args:
            buyer_type: 买家类型 (SMOKER/VIC/BOTH)
            limit: 返回数量
            offset: 偏移量

        Returns:
            买家列表
        """
        return self.queries.get_buyers_by_type(buyer_type, limit, offset)

    def get_vic_buyers(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取VIC买家列表

        性能: < 0.1秒 (使用vip_level索引)

        Args:
            limit: 返回数量
            offset: 偏移量

        Returns:
            VIC买家列表(按VIP等级排序)
        """
        return self.queries.get_vic_buyers(limit, offset)

    def get_smoker_buyers(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取Smoker买家列表

        性能: < 0.1秒 (使用l6m_netsales索引)

        Args:
            limit: 返回数量
            offset: 偏移量

        Returns:
            Smoker买家列表(按消费金额排序)
        """
        return self.queries.get_smoker_buyers(limit, offset)

    def get_churn_risk_buyers(
        self,
        risk_level: str = '高',
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取流失风险买家

        性能: < 0.1秒 (使用churn_risk索引)

        Args:
            risk_level: 风险等级 (高/中/低)
            limit: 返回数量
            offset: 偏移量

        Returns:
            流失风险买家列表
        """
        return self.queries.get_churn_risk_buyers(risk_level, limit, offset)

    def get_high_value_buyers(
        self,
        min_l6m_netsales: float = 5000,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取高价值买家(L6M消费 >= 阈值)

        性能: < 0.1秒 (使用l6m_netsales索引)

        Args:
            min_l6m_netsales: 最小近6个月消费金额
            limit: 返回数量
            offset: 偏移量

        Returns:
            高价值买家列表
        """
        return self.queries.get_high_value_buyers(min_l6m_netsales, limit, offset)

    def get_buyers_by_vip_level(
        self,
        vip_level: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        按VIP等级筛选买家

        性能: < 0.1秒 (使用vip_level索引)

        Args:
            vip_level: VIP等级 (V3/V2/V1/V0/Non-VIP)
            limit: 返回数量
            offset: 偏移量

        Returns:
            买家列表
        """
        return self.queries.get_buyers_by_vip_level(vip_level, limit, offset)

    def get_channel_stats(self) -> List[Dict[str, Any]]:
        """
        按渠道统计(DTC/PFS)

        性能: < 0.1秒 (使用channel索引)

        Returns:
            渠道统计数据列表
        """
        return self.queries.get_channel_stats()

    def get_actionable_customers(
        self,
        limit: int = 50
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取需要优先处理的客户(可操作客户列表)

        整合流失风险、高价值等需要关注的客户

        性能: < 0.5秒 (多次索引查询)

        Args:
            limit: 每个类别返回数量

        Returns:
            按问题类型分组的客户列表
        """
        # 高流失风险客户
        high_churn = self.get_churn_risk_buyers(risk_level='高', limit=limit)

        # 高价值客户(L6M消费 >= 10000)
        high_value = self.get_high_value_buyers(min_l6m_netsales=10000, limit=limit)

        # 中流失风险客户
        medium_churn = self.get_churn_risk_buyers(risk_level='中', limit=limit)

        return {
            "high_churn_risk": high_churn,
            "high_value": high_value,
            "medium_churn_risk": medium_churn
        }

    def get_buyers_by_rfm_segment(
        self,
        rfm_segment: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        按RFM客户分类筛选买家

        性能: < 0.1秒 (使用rfm_segment索引)

        Args:
            rfm_segment: RFM客户分类
                - 重要价值客户: 高频高消费且最近活跃
                - 重要发展客户: 高消费但频次低
                - 重要保持客户: 曾经高频高消费但近期沉默
                - 一般价值客户: 中等活跃度
                - 潜力客户: 新客户，有潜力
                - 流失预警: 曾经有价值但可能流失
                - 已流失: 长期无活动
            limit: 返回数量
            offset: 偏移量

        Returns:
            买家列表
        """
        query = """
            SELECT
                buyer_nick, channel, buyer_type, vip_level,
                historical_net_sales, total_orders,
                last_purchase_date, last_chat_date,
                rfm_recency_score, rfm_frequency_score, rfm_monetary_score,
                rfm_segment, churn_risk, city
            FROM target_buyers_precomputed
            WHERE rfm_segment = %s
            ORDER BY historical_net_sales DESC
            LIMIT %s OFFSET %s
        """

        return self.db.execute_query(query, [rfm_segment, limit, offset])

    def get_priority_customers(
        self,
        channel: Optional[Any] = None,
        buyer_type: Optional[Any] = None,
        follow_priority: Optional[Any] = None,
        sentiment_label: Optional[Any] = None,
        has_chat: Optional[str] = None,
        use_default_filter: bool = True,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取优先关注客户列表(带AI画像)

        性能: < 1秒 (JOIN + 索引查询)

        Args:
            channel: 渠道筛选 (DTC/PFS) 或 列表
            buyer_type: 买家类型筛选 (SMOKER/VIC/BOTH) 或 列表
            follow_priority: 跟进优先级筛选 (紧急/高/中/低) 或 列表
            sentiment_label: 情感标签筛选 (Positive/Neutral/Negative) 或 列表
            has_chat: 聊天状态筛选 ('yes'/'no')
            use_default_filter: 是否使用默认筛选 (follow_priority IN 紧急/高 OR sentiment_label = Negative)
            limit: 返回数量
            offset: 偏移量

        Returns:
            优先关注客户列表(包含AI画像)
        """
        return self.queries.get_priority_customers(
            channel=channel,
            buyer_type=buyer_type,
            follow_priority=follow_priority,
            sentiment_label=sentiment_label,
            has_chat=has_chat,
            use_default_filter=use_default_filter,
            limit=limit,
            offset=offset
        )

    def get_priority_customers_count(
        self,
        channel: Optional[Any] = None,
        buyer_type: Optional[Any] = None,
        follow_priority: Optional[Any] = None,
        sentiment_label: Optional[Any] = None,
        has_chat: Optional[str] = None,
        use_default_filter: bool = True
    ) -> int:
        """
        获取优先关注客户总数(用于分页)

        Args:
            同 get_priority_customers

        Returns:
            客户总数
        """
        return self.queries.get_priority_customers_count(
            channel=channel,
            buyer_type=buyer_type,
            follow_priority=follow_priority,
            sentiment_label=sentiment_label,
            has_chat=has_chat,
            use_default_filter=use_default_filter
        )
