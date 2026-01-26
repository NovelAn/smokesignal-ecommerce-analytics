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
        buyer_type: Optional[str] = None,
        vip_level: Optional[str] = None,
        channel: Optional[str] = None,
        sort_by: str = 'last_purchase',
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取所有目标买家列表(分页)

        Args:
            search: 昵称模糊搜索
            buyer_type: 买家类型筛选 (SMOKER/VIC/BOTH)
            vip_level: VIP等级筛选 (V3/V2/V1/V0/Non-VIP)
            channel: 渠道筛选 (DTC/PFS)
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
            conditions_to_remove.append('AND buyer_type = %(buyer_type)s')
        else:
            params['buyer_type'] = buyer_type

        if not vip_level:
            conditions_to_remove.append('AND vip_level = %(vip_level)s')
        else:
            params['vip_level'] = vip_level

        if not channel:
            conditions_to_remove.append('AND channel = %(channel)s')
        else:
            params['channel'] = channel

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
        buyer_type: Optional[str] = None,
        vip_level: Optional[str] = None,
        channel: Optional[str] = None
    ) -> int:
        """
        获取目标买家总数(用于分页)

        Args:
            buyer_type: 买家类型筛选
            vip_level: VIP等级筛选
            channel: 渠道筛选

        Returns:
            买家总数
        """
        # 构建WHERE条件
        where_clauses = []
        params = []

        if buyer_type:
            where_clauses.append("buyer_type = %s")
            params.append(buyer_type)

        if vip_level:
            where_clauses.append("vip_level = %s")
            params.append(vip_level)

        if channel:
            where_clauses.append("channel = %s")
            params.append(channel)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        sql = f"SELECT COUNT(*) as total FROM target_buyers_precomputed {where_sql}"

        result = self.db.execute_query(sql, tuple(params) if params else ())

        return result[0]['total'] if result else 0
