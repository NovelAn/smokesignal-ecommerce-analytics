"""
目标买家预计算表查询类
从SQL文件加载查询并执行,实现SQL与代码分离
"""
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from backend.database import Database


class TargetBuyerQueries:
    """
    目标买家预计算表查询类

    所有SQL查询存储在 backend/database/sql/target_buyers/ 目录
    这个类负责加载和执行这些SQL文件

    使用方式:
        queries = TargetBuyerQueries(db)
        result = queries.get_all_target_buyers(limit=100, offset=0)
    """

    def __init__(self, db: Database):
        """
        初始化查询类

        Args:
            db: 数据库连接实例
        """
        self.db = db
        # 获取SQL文件目录
        self.sql_dir = Path(__file__).parent / "sql" / "target_buyers"

        # 验证目录存在
        if not self.sql_dir.exists():
            raise FileNotFoundError(f"SQL查询目录不存在: {self.sql_dir}")

    def _load_sql(self, filename: str) -> str:
        """
        加载SQL文件内容

        Args:
            filename: SQL文件名(例如: get_all_target_buyers.sql)

        Returns:
            SQL查询字符串
        """
        sql_path = self.sql_dir / filename

        if not sql_path.exists():
            raise FileNotFoundError(f"SQL文件不存在: {sql_path}")

        with open(sql_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        # 移除SQL注释(可选,用于减少传输量)
        lines = [
            line for line in sql_content.split('\n')
            if not line.strip().startswith('--')
        ]

        return '\n'.join(lines)

    def get_all_target_buyers(
        self,
        search: Optional[str] = None,
        buyer_type: Optional[Any] = None,
        vip_level: Optional[Any] = None,
        channel: Optional[Any] = None,
        last_purchase_after: Optional[str] = None,
        chat_status: Optional[str] = None,
        sort_by: str = 'last_purchase',
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取所有目标买家列表(分页)

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
            买家列表
        """
        sql = self._load_sql('get_all_target_buyers.sql')

        # 构建动态WHERE子句
        conditions_to_remove = []
        params = {}

        # 处理LIKE查询的通配符
        if search:
            params['search'] = f"%{search}%"
        else:
            conditions_to_remove.append('AND buyer_nick LIKE %(search)s')

        # 处理可选筛选条件
        if not buyer_type:
            conditions_to_remove.append('AND buyer_type IN %(buyer_type)s')
        else:
            if isinstance(buyer_type, (list, tuple)):
                params['buyer_type'] = tuple(buyer_type)
            else:
                params['buyer_type'] = (buyer_type,)

        if not vip_level:
            conditions_to_remove.append('AND vip_level IN %(vip_level)s')
        else:
            if isinstance(vip_level, (list, tuple)):
                params['vip_level'] = tuple(vip_level)
            else:
                params['vip_level'] = (vip_level,)

        if not channel:
            conditions_to_remove.append('AND channel IN %(channel)s')
        else:
            if isinstance(channel, (list, tuple)):
                params['channel'] = tuple(channel)
            else:
                params['channel'] = (channel,)

        if not last_purchase_after:
            conditions_to_remove.append('AND last_purchase_date >= %(last_purchase_after)s')
        else:
            params['last_purchase_after'] = last_purchase_after

        # 处理聊天状态筛选
        # 逻辑：
        # 如果 chat_status 是 'chatted'，启用 AND last_chat_date IS NOT NULL ...
        # 如果 chat_status 是 'no_chat'，启用 AND last_chat_date IS NULL ...
        # 如果是其他或None，都移除
        
        if chat_status == 'chatted':
            params['chat_status'] = 'chatted'
            conditions_to_remove.append("AND last_chat_date IS NULL AND %(chat_status)s = 'no_chat'")
        elif chat_status == 'no_chat':
            params['chat_status'] = 'no_chat'
            conditions_to_remove.append("AND last_chat_date IS NOT NULL AND %(chat_status)s = 'chatted'")
        else:
            # 移除所有聊天相关的条件
            conditions_to_remove.append("AND last_chat_date IS NOT NULL AND %(chat_status)s = 'chatted'")
            conditions_to_remove.append("AND last_chat_date IS NULL AND %(chat_status)s = 'no_chat'")

        # 移除不需要的WHERE条件
        for condition in conditions_to_remove:
            sql = sql.replace(f'[[{condition}]]', '')

        # 清理剩余的[[ ]]标记
        import re
        sql = re.sub(r'\[\[|\]\]', '', sql)

        # 添加其他必需参数
        params['sort_by'] = sort_by
        params['limit'] = limit
        params['offset'] = offset

        return self.db.execute_query(sql, params)

    def get_target_buyer_by_nick(self, buyer_nick: str) -> Optional[Dict[str, Any]]:
        """
        根据买家昵称获取详细信息

        Args:
            buyer_nick: 买家昵称

        Returns:
            买家详细信息,如果不存在返回None
        """
        sql = self._load_sql('get_target_buyer_by_nick.sql')

        results = self.db.execute_query(sql, (buyer_nick,))

        return results[0] if results else None

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """
        获取Dashboard汇总指标

        Returns:
            包含所有指标的字典
        """
        sql = self._load_sql('get_dashboard_metrics.sql')

        results = self.db.execute_query(sql)

        return results[0] if results else {}

    def get_buyers_by_type(
        self,
        buyer_type: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        按买家类型筛选

        Args:
            buyer_type: 买家类型 (SMOKER/VIC/BOTH)
            limit: 返回数量
            offset: 偏移量

        Returns:
            买家列表
        """
        sql = self._load_sql('get_buyers_by_type.sql')

        return self.db.execute_query(sql, (buyer_type, limit, offset))

    def get_vic_buyers(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取VIC买家列表(按VIP等级排序)

        Args:
            limit: 返回数量
            offset: 偏移量

        Returns:
            VIC买家列表
        """
        sql = self._load_sql('get_vic_buyers.sql')

        return self.db.execute_query(sql, (limit, offset))

    def get_smoker_buyers(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取Smoker买家列表(按消费金额排序)

        Args:
            limit: 返回数量
            offset: 偏移量

        Returns:
            Smoker买家列表
        """
        sql = self._load_sql('get_smoker_buyers.sql')

        return self.db.execute_query(sql, (limit, offset))

    def get_churn_risk_buyers(
        self,
        risk_level: str = '高',
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取流失风险买家

        Args:
            risk_level: 风险等级 (高/中/低)
            limit: 返回数量
            offset: 偏移量

        Returns:
            流失风险买家列表
        """
        sql = self._load_sql('get_churn_risk_buyers.sql')

        return self.db.execute_query(sql, (risk_level, limit, offset))

    def get_high_value_buyers(
        self,
        min_l6m_netsales: float = 5000,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取高价值买家(L6M消费 >= 阈值)

        Args:
            min_l6m_netsales: 最小近6个月消费金额
            limit: 返回数量
            offset: 偏移量

        Returns:
            高价值买家列表
        """
        sql = self._load_sql('get_high_value_buyers.sql')

        return self.db.execute_query(sql, (min_l6m_netsales, limit, offset))

    def get_buyers_by_vip_level(
        self,
        vip_level: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        按VIP等级筛选买家

        Args:
            vip_level: VIP等级 (V3/V2/V1/V0/Non-VIP)
            limit: 返回数量
            offset: 偏移量

        Returns:
            买家列表
        """
        sql = self._load_sql('get_buyers_by_vip_level.sql')

        return self.db.execute_query(sql, (vip_level, limit, offset))

    def get_channel_stats(self) -> List[Dict[str, Any]]:
        """
        按渠道统计(DTC/PFS)

        Returns:
            渠道统计数据列表
        """
        sql = self._load_sql('get_channel_stats.sql')

        return self.db.execute_query(sql)

    def get_target_buyers_count(
        self,
        buyer_type: Optional[Any] = None,
        vip_level: Optional[Any] = None,
        channel: Optional[Any] = None,
        last_purchase_after: Optional[str] = None,
        chat_status: Optional[str] = None
    ) -> int:
        """
        获取目标买家总数(用于分页)

        Args:
            buyer_type: 买家类型筛选
            vip_level: VIP等级筛选
            channel: 渠道筛选
            last_purchase_after: 最后购买日期筛选
            chat_status: 聊天状态筛选

        Returns:
            买家总数
        """
        # 构建WHERE条件
        where_clauses = ["1=1"]
        params = []

        # 始终排除 SC/FF Flag 客户
        where_clauses.append("""
            NOT EXISTS (
                SELECT 1 
                FROM target_buyer_orders tbo 
                WHERE tbo.买家昵称 = target_buyers_precomputed.buyer_nick 
                AND (tbo.sc_flag = 1 OR tbo.ff_flag = 1)
            )
        """)

        if buyer_type:
            if isinstance(buyer_type, (list, tuple)):
                placeholders = ', '.join(['%s'] * len(buyer_type))
                where_clauses.append(f"buyer_type IN ({placeholders})")
                params.extend(buyer_type)
            else:
                where_clauses.append("buyer_type = %s")
                params.append(buyer_type)

        if vip_level:
            if isinstance(vip_level, (list, tuple)):
                placeholders = ', '.join(['%s'] * len(vip_level))
                where_clauses.append(f"vip_level IN ({placeholders})")
                params.extend(vip_level)
            else:
                where_clauses.append("vip_level = %s")
                params.append(vip_level)

        if channel:
            if isinstance(channel, (list, tuple)):
                placeholders = ', '.join(['%s'] * len(channel))
                where_clauses.append(f"channel IN ({placeholders})")
                params.extend(channel)
            else:
                where_clauses.append("channel = %s")
                params.append(channel)

        if last_purchase_after:
            where_clauses.append("last_purchase_date >= %s")
            params.append(last_purchase_after)

        if chat_status == 'chatted':
            where_clauses.append("last_chat_date IS NOT NULL")
        elif chat_status == 'no_chat':
            where_clauses.append("last_chat_date IS NULL")

        where_sql = "WHERE " + " AND ".join(where_clauses)

        sql = f"SELECT COUNT(*) as total FROM target_buyers_precomputed {where_sql}"

        result = self.db.execute_query(sql, tuple(params) if params else ())

        return result[0]['total'] if result else 0

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
        import re
        sql = self._load_sql('get_priority_customers.sql')

        # 构建动态WHERE子句
        conditions_to_remove = []
        params = {}

        # 渠道筛选
        if not channel:
            conditions_to_remove.append('AND tb.channel IN %(channel)s')
        else:
            if isinstance(channel, (list, tuple)):
                params['channel'] = tuple(channel)
            else:
                params['channel'] = (channel,)

        # 买家类型筛选
        if not buyer_type:
            conditions_to_remove.append('AND tb.buyer_type IN %(buyer_type)s')
        else:
            if isinstance(buyer_type, (list, tuple)):
                params['buyer_type'] = tuple(buyer_type)
            else:
                params['buyer_type'] = (buyer_type,)

        # 跟进优先级筛选
        if not follow_priority:
            conditions_to_remove.append('AND tb.follow_priority IN %(follow_priority)s')
        else:
            if isinstance(follow_priority, (list, tuple)):
                params['follow_priority'] = tuple(follow_priority)
            else:
                params['follow_priority'] = (follow_priority,)

        # 情感标签筛选
        if not sentiment_label:
            conditions_to_remove.append('AND COALESCE(ai.sentiment_label, tb.sentiment_label) IN %(sentiment_label)s')
        else:
            if isinstance(sentiment_label, (list, tuple)):
                params['sentiment_label'] = tuple(sentiment_label)
            else:
                params['sentiment_label'] = (sentiment_label,)

        # 聊天状态筛选
        if has_chat == 'yes':
            params['has_chat'] = 'yes'
            conditions_to_remove.append("AND tb.chat_frequency_days = 0 AND %(has_chat)s = 'no'")
        elif has_chat == 'no':
            params['has_chat'] = 'no'
            conditions_to_remove.append("AND tb.chat_frequency_days > 0 AND %(has_chat)s = 'yes'")
        else:
            conditions_to_remove.append("AND tb.chat_frequency_days > 0 AND %(has_chat)s = 'yes'")
            conditions_to_remove.append("AND tb.chat_frequency_days = 0 AND %(has_chat)s = 'no'")

        # 默认筛选逻辑
        if not use_default_filter:
            conditions_to_remove.append("AND (tb.follow_priority IN ('紧急', '高') OR COALESCE(ai.sentiment_label, tb.sentiment_label) = 'Negative')")

        # 移除不需要的WHERE条件
        for condition in conditions_to_remove:
            sql = sql.replace(f'[[{condition}]]', '')

        # 清理剩余的[[ ]]标记
        sql = re.sub(r'\[\[|\]\]', '', sql)

        # 添加分页参数
        params['limit'] = limit
        params['offset'] = offset

        return self.db.execute_query(sql, params)

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
        import re
        sql = self._load_sql('get_priority_customers_count.sql')

        # 构建动态WHERE子句 (与 get_priority_customers 相同的逻辑)
        conditions_to_remove = []
        params = {}

        if not channel:
            conditions_to_remove.append('AND tb.channel IN %(channel)s')
        else:
            if isinstance(channel, (list, tuple)):
                params['channel'] = tuple(channel)
            else:
                params['channel'] = (channel,)

        if not buyer_type:
            conditions_to_remove.append('AND tb.buyer_type IN %(buyer_type)s')
        else:
            if isinstance(buyer_type, (list, tuple)):
                params['buyer_type'] = tuple(buyer_type)
            else:
                params['buyer_type'] = (buyer_type,)

        if not follow_priority:
            conditions_to_remove.append('AND tb.follow_priority IN %(follow_priority)s')
        else:
            if isinstance(follow_priority, (list, tuple)):
                params['follow_priority'] = tuple(follow_priority)
            else:
                params['follow_priority'] = (follow_priority,)

        if not sentiment_label:
            conditions_to_remove.append('AND COALESCE(ai.sentiment_label, tb.sentiment_label) IN %(sentiment_label)s')
        else:
            if isinstance(sentiment_label, (list, tuple)):
                params['sentiment_label'] = tuple(sentiment_label)
            else:
                params['sentiment_label'] = (sentiment_label,)

        if has_chat == 'yes':
            params['has_chat'] = 'yes'
            conditions_to_remove.append("AND tb.chat_frequency_days = 0 AND %(has_chat)s = 'no'")
        elif has_chat == 'no':
            params['has_chat'] = 'no'
            conditions_to_remove.append("AND tb.chat_frequency_days > 0 AND %(has_chat)s = 'yes'")
        else:
            conditions_to_remove.append("AND tb.chat_frequency_days > 0 AND %(has_chat)s = 'yes'")
            conditions_to_remove.append("AND tb.chat_frequency_days = 0 AND %(has_chat)s = 'no'")

        if not use_default_filter:
            conditions_to_remove.append("AND (tb.follow_priority IN ('紧急', '高') OR COALESCE(ai.sentiment_label, tb.sentiment_label) = 'Negative')")

        for condition in conditions_to_remove:
            sql = sql.replace(f'[[{condition}]]', '')

        sql = re.sub(r'\[\[|\]\]', '', sql)

        result = self.db.execute_query(sql, params)

        return result[0]['total'] if result else 0
