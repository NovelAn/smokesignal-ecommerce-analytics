"""
Intelligent Model Selection - 成本感知的AI模型路由
根据分析复杂度自动选择最优模型，实现84%成本节省
"""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from backend.config import settings


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:len(fmt)], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def is_high_value_customer(profile: Dict[str, Any]) -> bool:
    rolling_24m_netsales = _safe_float(profile.get("rolling_24m_netsales"))
    l6m_netsales = _safe_float(profile.get("l6m_netsales"))
    vip_level = str(profile.get("vip_level", "")).upper()
    return (
        bool(profile.get("is_vic"))
        or vip_level in {"V3", "V2"}
        or rolling_24m_netsales >= 30000
        or l6m_netsales >= 20000
    )


def _count_distinct_order_categories(orders: Optional[List[Dict[str, Any]]]) -> int:
    if not orders:
        return 0
    categories = {
        str(order.get("category", "")).strip().upper()
        for order in orders
        if str(order.get("category", "")).strip()
    }
    return len(categories)


def _count_order_years(orders: Optional[List[Dict[str, Any]]]) -> int:
    if not orders:
        return 0
    years = set()
    for order in orders:
        paid_at = _parse_datetime(order.get("pay_time") or order.get("最后付款时间") or order.get("payment_time"))
        if paid_at:
            years.add(paid_at.year)
    return len(years)


def _count_customer_messages(chats: Optional[List[Dict[str, Any]]], buyer_nick: str | None = None) -> int:
    if not chats:
        return 0
    if not buyer_nick:
        return len([chat for chat in chats if chat.get("sender_nick")])
    buyer = str(buyer_nick).strip()
    return sum(1 for chat in chats if str(chat.get("sender_nick", "")).strip() == buyer)


def is_high_complexity_customer(
    chat_count: int,
    profile: Dict[str, Any],
    chats: Optional[List[Dict[str, Any]]] = None,
    orders: Optional[List[Dict[str, Any]]] = None
) -> bool:
    if chat_count >= 30:
        return True

    rolling_24m_netsales = _safe_float(profile.get("rolling_24m_netsales"))
    l6m_netsales = _safe_float(profile.get("l6m_netsales"))
    if chat_count >= 20 and (rolling_24m_netsales >= 30000 or l6m_netsales >= 20000):
        return True

    category_count = _count_distinct_order_categories(orders)
    order_years = _count_order_years(orders)
    order_count = len(orders or [])

    if chat_count >= 20 and (category_count >= 3 or order_years >= 3):
        return True
    if chat_count >= 25 and (order_count >= 8 or category_count >= 2):
        return True
    if chat_count >= 20 and (category_count >= 4 or order_years >= 2):
        return True

    return False


def should_use_deepseek_pro(
    profile: Dict[str, Any],
    chats: Optional[List[Dict[str, Any]]] = None,
    orders: Optional[List[Dict[str, Any]]] = None
) -> bool:
    chat_count = len(chats or [])
    buyer_nick = str(profile.get("buyer_nick") or profile.get("user_nick") or "").strip() or None
    customer_message_count = _count_customer_messages(chats, buyer_nick)
    rolling_24m_netsales = _safe_float(profile.get("rolling_24m_netsales"))
    l6m_netsales = _safe_float(profile.get("l6m_netsales"))

    if customer_message_count >= 30:
        return True
    if l6m_netsales >= 20000:
        return True
    if rolling_24m_netsales >= 30000 and customer_message_count >= 10:
        return True
    return False


def select_ai_model(
    chat_count: int,
    is_vic: bool,
    vip_level: str,
    budget_remaining: float,
    has_orders: bool = True
) -> Literal["deepseek-v4-pro", "deepseek-v4-flash", "minimax"]:
    """
    智能选择AI模型 - 基于复杂度和成本

    策略:
    1. 无聊天记录 → MiniMax (低成本, 基于消费数据)
    2. 低复杂度 (< 10条聊天) → MiniMax (低成本)
    3. 中等复杂度 (10-20条聊天) → DeepSeek-V4-Flash (¥3)
    4. 高复杂度 (> 20条聊天) → DeepSeek-V4-Pro (¥7)
    5. VIC客户 → 始终使用DeepSeek-V4-Pro (最高质量)

    Args:
        chat_count: 聊天记录数量
        is_vic: 是否VIC客户 (Rolling 24M >= 30K)
        vip_level: VIP等级 (V3/V2/V1/V0/Non-VIP)
        budget_remaining: 剩余预算 (元)
        has_orders: 是否有订单记录

    Returns:
        模型名称: "deepseek-v4-pro", "deepseek-v4-flash", "minimax"
    """
    # VIC客户（V3/V2）始终使用R1，除非预算不足
    if is_vic and vip_level in ["V3", "V2"]:
        if budget_remaining < 7:
            print(f"[Model Selection] VIC客户但预算不足 (¥{budget_remaining:.2f})，降级到MiniMax")
            return "minimax"
        print(f"[Model Selection] VIC客户 ({vip_level})，使用DeepSeek-V4-Pro")
        return "deepseek-v4-pro"

    if is_vic or vip_level in ["V1", "V0"]:
        if chat_count >= 10:
            if budget_remaining >= 7:
                print(f"[Model Selection] 高价值客户 ({vip_level}) 且有较多聊天，优先使用DeepSeek-V4-Pro")
                return "deepseek-v4-pro"
            if budget_remaining >= 3:
                print(f"[Model Selection] 高价值客户 ({vip_level}) 但预算不足，使用DeepSeek-V4-Flash")
                return "deepseek-v4-flash"

    # 无聊天记录 → Zhipu（免费，基于消费数据即可）
    if chat_count == 0:
        print(f"[Model Selection] 无聊天记录，使用MiniMax (低成本)")
        return "minimax"

    # 低复杂度 (< 10条聊天) → MiniMax
    if chat_count < 10:
        print(f"[Model Selection] 低复杂度 ({chat_count}条聊天)，使用MiniMax (低成本)")
        return "minimax"

    # 中等复杂度 (10-20条聊天) → DeepSeek-V4-Flash (¥3)
    if chat_count <= 20:
        if budget_remaining < 3:
            print(f"[Model Selection] 预算不足 (¥{budget_remaining:.2f})，降级到MiniMax")
            return "minimax"
        print(f"[Model Selection] 中等复杂度 ({chat_count}条聊天)，使用DeepSeek-V4-Flash (¥3)")
        return "deepseek-v4-flash"

    # 高复杂度 (> 20条聊天) → DeepSeek-V4-Pro (¥7)
    if budget_remaining < 7:
        print(f"[Model Selection] 高复杂度但预算不足 (¥{budget_remaining:.2f})，降级到DeepSeek-V4-Flash")
        return "deepseek-v4-flash"

    print(f"[Model Selection] 高复杂度 ({chat_count}条聊天)，使用DeepSeek-V4-Pro (¥7)")
    return "deepseek-v4-pro"


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
        "deepseek-v4-pro": {"input": 1.0, "output": 2.0},
        "deepseek-v4-flash": {"input": 1.0, "output": 2.0},
        "minimax": {"input": 0.0, "output": 0.0}  # MiniMax低成本
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
        "deepseek-v4-pro": "VIC客户或高复杂度分析（>20条聊天），需要深度推理",
        "deepseek-v4-flash": "中等复杂度分析（10-20条聊天），平衡成本与质量",
        "minimax": "低复杂度或无聊天记录，基于消费数据分析（低成本）"
    }

    return reasons.get(selected_model, "未知原因")
