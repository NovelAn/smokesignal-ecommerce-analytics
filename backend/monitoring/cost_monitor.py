"""
Cost Monitor - API成本实时监控
支持数据库持久化和历史分析
"""
import time
from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
from collections import defaultdict
import pymysql

from backend.config import settings
from backend.database.db_config_manager import DBConfigManager


class CostMonitor:
    """
    API成本实时监控

    记录每次API调用的token使用和成本
    """

    # 定价表（元/1M tokens）
    PRICING = {
        "deepseek-reasoner": {"input": 1.0, "output": 2.0},
        "deepseek-chat": {"input": 1.0, "output": 2.0},
        "glm-4-plus": {"input": 0.5, "output": 2.0}
    }

    def __init__(self, daily_budget: float = 50.0):
        """
        初始化成本监控器

        Args:
            daily_budget: 每日预算（元）
        """
        self.daily_budget = daily_budget
        self.daily_records: List[Dict] = []
        self.daily_cost = 0.0
        self.daily_calls = 0
        self.db_conn = None

        # 按模型统计
        self.model_stats = defaultdict(lambda: {
            "calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0.0
        })

        # 尝试加载今日数据库统计
        try:
            self._load_daily_summary()
        except Exception as e:
            print(f"[成本] 数据库加载失败（首次运行或数据库未配置）: {e}")

    def log_api_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        buyer_nick: str = "",
        method: str = ""
    ):
        """
        记录API调用

        Args:
            model: 模型名称
            input_tokens: 输入token数
            output_tokens: 输出token数
            buyer_nick: 买家昵称（可选）
            method: 分析方法（可选）
        """
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        self.daily_calls += 1
        self.daily_cost += cost

        # 记录详情
        record = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": cost,
            "buyer_nick": buyer_nick,
            "method": method
        }
        self.daily_records.append(record)

        # 更新模型统计
        self.model_stats[model]["calls"] += 1
        self.model_stats[model]["input_tokens"] += input_tokens
        self.model_stats[model]["output_tokens"] += output_tokens
        self.model_stats[model]["cost"] += cost

        # 持久化到数据库
        self._persist_to_database(record)

        print(f"[成本] {model}: {cost:.4f}元 (本次调用) - 总计: ¥{self.daily_cost:.2f}")

        # 预算预警
        self.check_budget_alert()

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        计算成本

        Args:
            model: 模型名称
            input_tokens: 输入token数
            output_tokens: 输出token数

        Returns:
            成本（元）
        """
        if model not in self.PRICING:
            # 未知模型，默认价格
            return (input_tokens + output_tokens) * 0.001 / 1000

        pricing = self.PRICING[model]
        input_cost = input_tokens * pricing["input"] / 1_000_000
        output_cost = output_tokens * pricing["output"] / 1_000_000

        return input_cost + output_cost

    def check_budget_alert(self):
        """预算预警"""
        usage_rate = self.daily_cost / self.daily_budget if self.daily_budget > 0 else 0

        if usage_rate >= 1.0:
            print(f"⚠️⚠️⚠️ 预算超支：今日已使用 ¥{self.daily_cost:.2f}，预算 ¥{self.daily_budget:.2f}")
        elif usage_rate >= 0.8:
            print(f"⚠️⚠️ 预算预警：今日已使用 ¥{self.daily_cost:.2f}（{usage_rate:.1%}），预算 ¥{self.daily_budget:.2f}")
        elif usage_rate >= 0.5:
            print(f"⚠️ 预算提醒：今日已使用 ¥{self.daily_cost:.2f}（{usage_rate:.1%}），预算 ¥{self.daily_budget:.2f}")

    def get_daily_summary(self) -> Dict:
        """
        获取每日汇总

        Returns:
            {
                "date": date,
                "调用次数": int,
                "总成本": float,
                "平均成本": float,
                "预算使用率": float,
                "模型统计": Dict
            }
        """
        avg_cost = self.daily_cost / self.daily_calls if self.daily_calls > 0 else 0
        budget_rate = self.daily_cost / self.daily_budget if self.daily_budget > 0 else 0

        return {
            "date": str(date.today()),
            "调用次数": self.daily_calls,
            "总成本": round(self.daily_cost, 2),
            "平均成本": round(avg_cost, 4),
            "预算使用率": round(budget_rate, 2),
            "模型统计": dict(self.model_stats),
            "预算余额": round(self.daily_budget - self.daily_cost, 2)
        }

    def get_model_summary(self, model: str) -> Dict:
        """
        获取特定模型的统计

        Args:
            model: 模型名称

        Returns:
            模型统计信息
        """
        if model not in self.model_stats:
            return {"error": f"模型 {model} 暂无记录"}

        stats = self.model_stats[model]
        avg_tokens = (stats["input_tokens"] + stats["output_tokens"]) / stats["calls"] if stats["calls"] > 0 else 0

        return {
            "模型": model,
            "调用次数": stats["calls"],
            "总token数": stats["input_tokens"] + stats["output_tokens"],
            "平均token数": round(avg_tokens, 0),
            "总成本": round(stats["cost"], 2),
            "平均成本": round(stats["cost"] / stats["calls"], 4) if stats["calls"] > 0 else 0
        }

    def reset_daily(self):
        """重置每日统计"""
        self.daily_records = []
        self.daily_cost = 0.0
        self.daily_calls = 0
        self.model_stats = defaultdict(lambda: {
            "calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0.0
        })
        print(f"[成本] 每日统计已重置 - {date.today()}")

    def _get_db_connection(self):
        """获取数据库连接"""
        if self.db_conn is None or not self.db_conn.open:
            try:
                db_configs = DBConfigManager.get_db_config_for_pymysql()
                db_name = settings.db_name_to_use if settings.db_name_to_use else ""

                # 查找匹配的数据库配置
                db_config = None
                for config in db_configs:
                    if config["database"] == db_name:
                        db_config = config
                        break

                # 如果没找到，使用第一个配置（通常是唯一配置）
                if db_config is None and len(db_configs) > 0:
                    db_config = db_configs[0]
                    print(f"[成本] 使用数据库配置: {db_config['database']}")

                if db_config is None:
                    print(f"[成本] 未找到数据库配置: {db_name}")
                    return None

                self.db_conn = pymysql.connect(**db_config)
                print(f"[成本] 数据库连接成功: {db_config['database']}")
            except Exception as e:
                print(f"[成本] 数据库连接失败: {e}")
                return None

        return self.db_conn

    def _load_daily_summary(self):
        """从数据库加载今日统计"""
        conn = self._get_db_connection()
        if conn is None:
            return

        try:
            with conn.cursor() as cursor:
                # 查询今日汇总
                cursor.execute(
                    "SELECT * FROM ai_cost_daily_summary WHERE date = %s",
                    (date.today(),)
                )
                summary = cursor.fetchone()

                if summary:
                    # 加载到内存
                    self.daily_calls = summary["total_calls"]
                    self.daily_cost = float(summary["total_cost"])

                    # 加载模型统计
                    cursor.execute(
                        """
                        SELECT model, COUNT(*) as calls, SUM(cost) as cost,
                               SUM(input_tokens) as input_tokens,
                               SUM(output_tokens) as output_tokens
                        FROM ai_cost_log
                        WHERE DATE(timestamp) = %s
                        GROUP BY model
                        """,
                        (date.today(),)
                    )

                    for row in cursor.fetchall():
                        model = row["model"]
                        self.model_stats[model] = {
                            "calls": row["calls"],
                            "input_tokens": row["input_tokens"],
                            "output_tokens": row["output_tokens"],
                            "cost": float(row["cost"])
                        }

                    print(f"[成本] 已加载今日统计: {self.daily_calls}次调用, ¥{self.daily_cost:.2f}")
        except Exception as e:
            print(f"[成本] 加载今日统计失败: {e}")

    def _persist_to_database(self, record: Dict):
        """持久化API调用记录到数据库"""
        conn = self._get_db_connection()
        if conn is None:
            return

        try:
            with conn.cursor() as cursor:
                # 插入详细日志
                cursor.execute(
                    """
                    INSERT INTO ai_cost_log
                    (timestamp, model, input_tokens, output_tokens, total_tokens, cost, buyer_nick, method)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record["timestamp"],
                        record["model"],
                        record["input_tokens"],
                        record["output_tokens"],
                        record["total_tokens"],
                        record["cost"],
                        record.get("buyer_nick", ""),
                        record.get("method", "")
                    )
                )

                # 更新或插入每日汇总
                cursor.execute(
                    """
                    INSERT INTO ai_cost_daily_summary
                    (date, total_calls, total_cost, budget, budget_usage_rate)
                    VALUES (%s, 1, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        total_calls = total_calls + 1,
                        total_cost = total_cost + %s,
                        budget_usage_rate = (total_cost + %s) / budget * 100
                    """,
                    (date.today(), record["cost"], self.daily_budget,
                     record["cost"] / self.daily_budget * 100 if self.daily_budget > 0 else 0,
                     record["cost"], record["cost"])
                )

                # 更新模型特定统计
                model = record["model"]
                if "deepseek-reasoner" in model:
                    cursor.execute(
                        """
                        INSERT INTO ai_cost_daily_summary
                        (date, deepseek_r1_calls, deepseek_r1_cost)
                        VALUES (%s, 1, %s)
                        ON DUPLICATE KEY UPDATE
                            deepseek_r1_calls = deepseek_r1_calls + 1,
                            deepseek_r1_cost = deepseek_r1_cost + %s
                        """,
                        (date.today(), record["cost"], record["cost"])
                    )
                elif "deepseek-chat" in model:
                    cursor.execute(
                        """
                        INSERT INTO ai_cost_daily_summary
                        (date, deepseek_chat_calls, deepseek_chat_cost)
                        VALUES (%s, 1, %s)
                        ON DUPLICATE KEY UPDATE
                            deepseek_chat_calls = deepseek_chat_calls + 1,
                            deepseek_chat_cost = deepseek_chat_cost + %s
                        """,
                        (date.today(), record["cost"], record["cost"])
                    )
                elif "glm" in model.lower():
                    cursor.execute(
                        """
                        INSERT INTO ai_cost_daily_summary
                        (date, zhipu_calls, zhipu_cost)
                        VALUES (%s, 1, %s)
                        ON DUPLICATE KEY UPDATE
                            zhipu_calls = zhipu_calls + 1,
                            zhipu_cost = zhipu_cost + %s
                        """,
                        (date.today(), record["cost"], record["cost"])
                    )

                # 更新小时统计
                current_datetime = datetime.fromisoformat(record["timestamp"])
                cursor.execute(
                    """
                    INSERT INTO ai_cost_hourly
                    (date, hour, model, calls, cost, tokens)
                    VALUES (%s, %s, %s, 1, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        calls = calls + 1,
                        cost = cost + %s,
                        tokens = tokens + %s
                    """,
                    (current_datetime.date(), current_datetime.hour, model,
                     record["cost"], record["total_tokens"],
                     record["cost"], record["total_tokens"])
                )

                conn.commit()
        except Exception as e:
            print(f"[成本] 数据库持久化失败: {e}")
            conn.rollback()

    def get_monthly_summary(self, year: int, month: int) -> Dict:
        """
        获取月度汇总

        Args:
            year: 年份
            month: 月份 (1-12)

        Returns:
            月度统计
        """
        conn = self._get_db_connection()
        if conn is None:
            return {"error": "数据库未连接"}

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) as total_calls,
                        SUM(cost) as total_cost,
                        SUM(input_tokens) as input_tokens,
                        SUM(output_tokens) as output_tokens,
                        COUNT(DISTINCT buyer_nick) as unique_buyers
                    FROM ai_cost_log
                    WHERE YEAR(timestamp) = %s AND MONTH(timestamp) = %s
                    """,
                    (year, month)
                )
                row = cursor.fetchone()

                return {
                    "year": year,
                    "month": month,
                    "total_calls": row["total_calls"] or 0,
                    "total_cost": float(row["total_cost"]) if row["total_cost"] else 0.0,
                    "input_tokens": row["input_tokens"] or 0,
                    "output_tokens": row["output_tokens"] or 0,
                    "unique_buyers": row["unique_buyers"] or 0
                }
        except Exception as e:
            return {"error": str(e)}

    def get_hourly_costs_today(self) -> List[Dict]:
        """
        获取今日每小时成本

        Returns:
            [{"hour": 0, "cost": 1.23}, ...]
        """
        conn = self._get_db_connection()
        if conn is None:
            return []

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT hour, SUM(cost) as cost, SUM(calls) as calls
                    FROM ai_cost_hourly
                    WHERE date = %s
                    GROUP BY hour
                    ORDER BY hour
                    """,
                    (date.today(),)
                )
                rows = cursor.fetchall()

                return [
                    {
                        "hour": row["hour"],
                        "cost": float(row["cost"]),
                        "calls": row["calls"]
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"[成本] 获取小时统计失败: {e}")
            return []

    def get_cost_by_model(self, start_date: date, end_date: date) -> Dict:
        """
        获取按模型分组的成本统计

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            模型成本统计
        """
        conn = self._get_db_connection()
        if conn is None:
            return {}

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        model,
                        COUNT(*) as calls,
                        SUM(cost) as cost,
                        SUM(input_tokens) as input_tokens,
                        SUM(output_tokens) as output_tokens
                    FROM ai_cost_log
                    WHERE DATE(timestamp) BETWEEN %s AND %s
                    GROUP BY model
                    ORDER BY cost DESC
                    """,
                    (start_date, end_date)
                )
                rows = cursor.fetchall()

                return {
                    row["model"]: {
                        "calls": row["calls"],
                        "cost": float(row["cost"]),
                        "input_tokens": row["input_tokens"],
                        "output_tokens": row["output_tokens"]
                    }
                    for row in rows
                }
        except Exception as e:
            print(f"[成本] 获取模型统计失败: {e}")
            return {}


# 全局单例
_cost_monitor_instance = None


def get_cost_monitor() -> CostMonitor:
    """获取成本监控器单例"""
    global _cost_monitor_instance
    if _cost_monitor_instance is None:
        _cost_monitor_instance = CostMonitor()
    return _cost_monitor_instance
