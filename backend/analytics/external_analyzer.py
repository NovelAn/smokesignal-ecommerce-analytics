"""
场外信息分析器 - External Records Analyzer

管理客户的场外信息（线下消费、私域沟通记录）
"""
from typing import List, Dict, Any, Optional
from datetime import date, datetime
import logging

from backend.database import Database
from backend.config import settings


class ExternalAnalyzer:
    """场外信息分析器"""

    def __init__(self, db_name: Optional[str] = None):
        """初始化分析器"""
        self.db_name = db_name or settings.db_name_to_use or 'aliyunDB'
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """确保表存在"""
        try:
            db = Database(db_name=self.db_name)
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS external_records (
                  id INT AUTO_INCREMENT PRIMARY KEY,
                  user_nick VARCHAR(100) NOT NULL COMMENT '客户昵称',
                  record_type ENUM('communication', 'purchase') NOT NULL COMMENT '类型',
                  record_date DATE NOT NULL COMMENT '日期',
                  channel VARCHAR(100) COMMENT '渠道',
                  content TEXT COMMENT '内容描述',
                  notes TEXT COMMENT '备注',
                  amount DECIMAL(10, 2) COMMENT '消费金额',
                  category VARCHAR(50) COMMENT '商品品类',
                  created_by VARCHAR(50) COMMENT '录入人',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  INDEX idx_user_nick (user_nick),
                  INDEX idx_record_type (record_type),
                  INDEX idx_record_date (record_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            db.execute_update(create_table_sql)
            logging.info("[ExternalAnalyzer] Table external_records verified/created")
        except Exception as e:
            logging.warning(f"[ExternalAnalyzer] Could not verify table: {e}")

    def get_records(
        self,
        search: Optional[str] = None,
        record_type: Optional[str] = None,
        channel: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        获取场外记录列表（支持分页和筛选）

        Args:
            search: 按客户昵称搜索
            record_type: 记录类型 (communication/purchase)
            channel: 渠道筛选
            date_from: 开始日期
            date_to: 结束日期
            limit: 返回数量
            offset: 偏移量

        Returns:
            {
                "records": [...],
                "total": int,
                "limit": int,
                "offset": int
            }
        """
        db = Database(db_name=self.db_name)

        # 构建查询条件
        conditions = []
        params = []

        if search:
            conditions.append("user_nick LIKE %s")
            params.append(f"%{search}%")

        if record_type:
            conditions.append("record_type = %s")
            params.append(record_type)

        if channel:
            conditions.append("channel LIKE %s")
            params.append(f"%{channel}%")

        if date_from:
            conditions.append("record_date >= %s")
            params.append(date_from)

        if date_to:
            conditions.append("record_date <= %s")
            params.append(date_to)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 查询总数
        count_query = f"SELECT COUNT(*) as total FROM external_records WHERE {where_clause}"
        total_result = db.execute_query(count_query, params)
        total = total_result[0].get('total', 0) if total_result else 0

        # 查询记录
        query = f"""
            SELECT
                id, user_nick, record_type, record_date, channel,
                content, notes, amount, category, created_by,
                created_at, updated_at
            FROM external_records
            WHERE {where_clause}
            ORDER BY record_date DESC, created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        records = db.execute_query(query, params)

        # 格式化日期和金额
        formatted_records = []
        for r in records:
            formatted_records.append({
                "id": str(r.get("id")),
                "user_nick": r.get("user_nick"),
                "record_type": r.get("record_type"),
                "record_date": str(r.get("record_date")) if r.get("record_date") else None,
                "channel": r.get("channel"),
                "content": r.get("content"),
                "notes": r.get("notes"),
                "amount": float(r.get("amount")) if r.get("amount") else None,
                "category": r.get("category"),
                "created_by": r.get("created_by"),
                "created_at": str(r.get("created_at")) if r.get("created_at") else None,
                "updated_at": str(r.get("updated_at")) if r.get("updated_at") else None
            })

        return {
            "records": formatted_records,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    def get_record_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        """获取单条记录"""
        db = Database(db_name=self.db_name)

        query = """
            SELECT
                id, user_nick, record_type, record_date, channel,
                content, notes, amount, category, created_by,
                created_at, updated_at
            FROM external_records
            WHERE id = %s
        """
        result = db.execute_query(query, [record_id])

        if not result:
            return None

        r = result[0]
        return {
            "id": str(r.get("id")),
            "user_nick": r.get("user_nick"),
            "record_type": r.get("record_type"),
            "record_date": str(r.get("record_date")) if r.get("record_date") else None,
            "channel": r.get("channel"),
            "content": r.get("content"),
            "notes": r.get("notes"),
            "amount": float(r.get("amount")) if r.get("amount") else None,
            "category": r.get("category"),
            "created_by": r.get("created_by"),
            "created_at": str(r.get("created_at")) if r.get("created_at") else None,
            "updated_at": str(r.get("updated_at")) if r.get("updated_at") else None
        }

    def get_records_by_user(self, user_nick: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取某客户的所有场外记录

        用于 AI 分析时获取补充上下文
        """
        db = Database(db_name=self.db_name)

        query = """
            SELECT
                id, user_nick, record_type, record_date, channel,
                content, notes, amount, category, created_by,
                created_at, updated_at
            FROM external_records
            WHERE user_nick = %s
            ORDER BY record_date DESC
            LIMIT %s
        """
        records = db.execute_query(query, [user_nick, limit])

        formatted_records = []
        for r in records:
            formatted_records.append({
                "id": str(r.get("id")),
                "user_nick": r.get("user_nick"),
                "record_type": r.get("record_type"),
                "record_date": str(r.get("record_date")) if r.get("record_date") else None,
                "channel": r.get("channel"),
                "content": r.get("content"),
                "notes": r.get("notes"),
                "amount": float(r.get("amount")) if r.get("amount") else None,
                "category": r.get("category"),
                "created_by": r.get("created_by"),
                "created_at": str(r.get("created_at")) if r.get("created_at") else None,
                "updated_at": str(r.get("updated_at")) if r.get("updated_at") else None
            })

        return formatted_records

    def create_record(
        self,
        user_nick: str,
        record_type: str,
        record_date: str,
        channel: Optional[str] = None,
        content: Optional[str] = None,
        notes: Optional[str] = None,
        amount: Optional[float] = None,
        category: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建场外记录

        Args:
            user_nick: 客户昵称
            record_type: 记录类型 (communication/purchase)
            record_date: 日期 (YYYY-MM-DD)
            channel: 渠道
            content: 内容描述
            notes: 备注
            amount: 消费金额（仅消费类型）
            category: 商品品类（仅消费类型）
            created_by: 录入人

        Returns:
            创建的记录
        """
        db = Database(db_name=self.db_name)

        query = """
            INSERT INTO external_records
            (user_nick, record_type, record_date, channel, content, notes, amount, category, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = [
            user_nick, record_type, record_date, channel, content,
            notes, amount, category, created_by
        ]

        record_id = db.execute_update(query, params)
        logging.info(f"[ExternalAnalyzer] Created record {record_id} for user {user_nick}")

        return self.get_record_by_id(record_id)

    def update_record(
        self,
        record_id: int,
        user_nick: Optional[str] = None,
        record_type: Optional[str] = None,
        record_date: Optional[str] = None,
        channel: Optional[str] = None,
        content: Optional[str] = None,
        notes: Optional[str] = None,
        amount: Optional[float] = None,
        category: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        更新场外记录
        """
        db = Database(db_name=self.db_name)

        # 构建更新字段
        updates = []
        params = []

        if user_nick is not None:
            updates.append("user_nick = %s")
            params.append(user_nick)

        if record_type is not None:
            updates.append("record_type = %s")
            params.append(record_type)

        if record_date is not None:
            updates.append("record_date = %s")
            params.append(record_date)

        if channel is not None:
            updates.append("channel = %s")
            params.append(channel)

        if content is not None:
            updates.append("content = %s")
            params.append(content)

        if notes is not None:
            updates.append("notes = %s")
            params.append(notes)

        if amount is not None:
            updates.append("amount = %s")
            params.append(amount)

        if category is not None:
            updates.append("category = %s")
            params.append(category)

        if not updates:
            return self.get_record_by_id(record_id)

        params.append(record_id)
        query = f"UPDATE external_records SET {', '.join(updates)} WHERE id = %s"

        db.execute_update(query, params)
        logging.info(f"[ExternalAnalyzer] Updated record {record_id}")

        return self.get_record_by_id(record_id)

    def delete_record(self, record_id: int) -> bool:
        """删除场外记录"""
        db = Database(db_name=self.db_name)

        query = "DELETE FROM external_records WHERE id = %s"
        affected = db.execute_update(query, [record_id])

        if affected > 0:
            logging.info(f"[ExternalAnalyzer] Deleted record {record_id}")
            return True
        return False

    def batch_import(self, records: List[Dict[str, Any]], created_by: Optional[str] = None) -> Dict[str, Any]:
        """
        批量导入场外记录

        Args:
            records: 记录列表
            created_by: 录入人

        Returns:
            {
                "success_count": int,
                "failed_count": int,
                "errors": [str, ...]
            }
        """
        success_count = 0
        failed_count = 0
        errors = []

        for i, record in enumerate(records):
            try:
                self.create_record(
                    user_nick=record.get("user_nick"),
                    record_type=record.get("record_type"),
                    record_date=record.get("record_date"),
                    channel=record.get("channel"),
                    content=record.get("content"),
                    notes=record.get("notes"),
                    amount=float(record.get("amount")) if record.get("amount") else None,
                    category=record.get("category"),
                    created_by=created_by or record.get("created_by")
                )
                success_count += 1
            except Exception as e:
                failed_count += 1
                errors.append(f"Row {i + 1}: {str(e)}")
                logging.error(f"[ExternalAnalyzer] Import error at row {i + 1}: {e}")

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors[:10]  # 只返回前10个错误
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取场外信息统计

        Returns:
            {
                "total_records": int,
                "communication_count": int,
                "purchase_count": int,
                "total_offline_amount": float,
                "top_channels": [...],
                "recent_records": [...]
            }
        """
        db = Database(db_name=self.db_name)

        # 总数和类型统计
        stats_query = """
            SELECT
                COUNT(*) as total_records,
                SUM(CASE WHEN record_type = 'communication' THEN 1 ELSE 0 END) as communication_count,
                SUM(CASE WHEN record_type = 'purchase' THEN 1 ELSE 0 END) as purchase_count,
                SUM(CASE WHEN record_type = 'purchase' THEN amount ELSE 0 END) as total_offline_amount
            FROM external_records
        """
        stats = db.execute_query(stats_query)

        # 渠道分布
        channels_query = """
            SELECT channel, COUNT(*) as count
            FROM external_records
            WHERE channel IS NOT NULL AND channel != ''
            GROUP BY channel
            ORDER BY count DESC
            LIMIT 10
        """
        channels = db.execute_query(channels_query)

        # 最近记录
        recent_query = """
            SELECT user_nick, record_type, record_date, channel, amount
            FROM external_records
            ORDER BY created_at DESC
            LIMIT 5
        """
        recent = db.execute_query(recent_query)

        if stats:
            stat = stats[0]
            return {
                "total_records": stat.get("total_records", 0),
                "communication_count": stat.get("communication_count", 0) or 0,
                "purchase_count": stat.get("purchase_count", 0) or 0,
                "total_offline_amount": float(stat.get("total_offline_amount") or 0),
                "top_channels": channels,
                "recent_records": recent
            }

        return {
            "total_records": 0,
            "communication_count": 0,
            "purchase_count": 0,
            "total_offline_amount": 0,
            "top_channels": [],
            "recent_records": []
        }


# 单例实例
_external_analyzer = None


def get_external_analyzer() -> ExternalAnalyzer:
    """获取场外信息分析器单例"""
    global _external_analyzer
    if _external_analyzer is None:
        _external_analyzer = ExternalAnalyzer()
    return _external_analyzer
