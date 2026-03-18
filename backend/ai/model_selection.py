"""
Intelligent Model Selection - 成本感知的AI模型路由
根据分析复杂度自动选择最优模型，实现84%成本节省
"""
from typing import Literal
from backend.config import settings


def select_ai_model(
    chat_count: int,
    is_vic: bool,
    vip_level: str,
    budget_remaining: float,
    has_orders: bool = True
) -> Literal["deepseek-r1", "deepseek-chat", "zhipu"]:
    """
    智能选择AI模型 - 基于复杂度和成本

    策略:
    1. 无聊天记录 → Zhipu (免费, 基于消费数据)
    2. 低复杂度 (< 10条聊天) → Zhipu (免费)
    3. 中等复杂度 (10-20条聊天) → DeepSeek-Chat (¥3)
    4. 高复杂度 (> 20条聊天) → DeepSeek-R1 (¥7)
    5. VIC客户 → 始终使用DeepSeek-R1 (最高质量)

    Args:
        chat_count: 聊天记录数量
        is_vic: 是否VIC客户 (Rolling 24M >= 30K)
        vip_level: VIP等级 (V3/V2/V1/V0/Non-VIP)
        budget_remaining: 剩余预算 (元)
        has_orders: 是否有订单记录

    Returns:
        模型名称: "deepseek-r1", "deepseek-chat", "zhipu"
    """
    # VIC客户（V3/V2）始终使用R1，除非预算不足
    if is_vic and vip_level in ["V3", "V2"]:
        if budget_remaining < 7:
            print(f"[Model Selection] VIC客户但预算不足 (¥{budget_remaining:.2f})，降级到Zhipu")
            return "zhipu"
        print(f"[Model Selection] VIC客户 ({vip_level})，使用DeepSeek-R1")
        return "deepseek-r1"

    # 无聊天记录 → Zhipu（免费，基于消费数据即可）
    if chat_count == 0:
        print(f"[Model Selection] 无聊天记录，使用Zhipu (免费)")
        return "zhipu"

    # 低复杂度 (< 10条聊天) → Zhipu
    if chat_count < 10:
        print(f"[Model Selection] 低复杂度 ({chat_count}条聊天)，使用Zhipu (免费)")
        return "zhipu"

    # 中等复杂度 (10-20条聊天) → DeepSeek-Chat (¥3)
    if chat_count <= 20:
        if budget_remaining < 3:
            print(f"[Model Selection] 预算不足 (¥{budget_remaining:.2f})，降级到Zhipu")
            return "zhipu"
        print(f"[Model Selection] 中等复杂度 ({chat_count}条聊天)，使用DeepSeek-Chat (¥3)")
        return "deepseek-chat"

    # 高复杂度 (> 20条聊天) → DeepSeek-R1 (¥7)
    if budget_remaining < 7:
        print(f"[Model Selection] 高复杂度但预算不足 (¥{budget_remaining:.2f})，降级到DeepSeek-Chat")
        return "deepseek-chat"

    print(f"[Model Selection] 高复杂度 ({chat_count}条聊天)，使用DeepSeek-R1 (¥7)")
    return "deepseek-r1"


def estimate_cost(
    model: str,
    estimated_input_tokens: int = 2000,
    estimated_output_tokens: int = 1000
) -> float:
    """
    估算API调用成本

    Args:
        model: 模型名称
        estimated_input_tokens: 预估输入token数
        estimated_output_tokens: 预估输出token数

    Returns:
        预估成本（元）
    """
    # 定价表（元/1M tokens）
    pricing = {
        "deepseek-r1": {"input": 1.0, "output": 2.0},
        "deepseek-chat": {"input": 1.0, "output": 2.0},
        "zhipu": {"input": 0.0, "output": 0.0}  # Zhipu免费（有月度套餐）
    }

    if model not in pricing:
        return 0.0

    model_pricing = pricing[model]
    input_cost = estimated_input_tokens * model_pricing["input"] / 1_000_000
    output_cost = estimated_output_tokens * model_pricing["output"] / 1_000_000

    return input_cost + output_cost


def get_model_selection_reason(
    chat_count: int,
    is_vic: bool,
    vip_level: str,
    selected_model: str
) -> str:
    """
    获取模型选择的原因说明（用于日志和调试）

    Args:
        chat_count: 聊天记录数量
        is_vic: 是否VIC客户
        vip_level: VIP等级
        selected_model: 选中的模型

    Returns:
        原因说明
    """
    reasons = {
        "deepseek-r1": "VIC客户或高复杂度分析（>20条聊天），需要深度推理",
        "deepseek-chat": "中等复杂度分析（10-20条聊天），平衡成本与质量",
        "zhipu": "低复杂度或无聊天记录，基于消费数据分析（免费）"
    }

    return reasons.get(selected_model, "未知原因")
