"""
Cost Monitor - API成本实时监控
"""
import time
from typing import Dict, List
from datetime import datetime, date
from collections import defaultdict


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

        # 按模型统计
        self.model_stats = defaultdict(lambda: {
            "calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0.0
        })

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


# 全局单例
_cost_monitor_instance = None


def get_cost_monitor() -> CostMonitor:
    """获取成本监控器单例"""
    global _cost_monitor_instance
    if _cost_monitor_instance is None:
        _cost_monitor_instance = CostMonitor()
    return _cost_monitor_instance
