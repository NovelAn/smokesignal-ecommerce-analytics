"""
Behavior Analyzer - 订单行为结构化分析
"""
from typing import Dict, List, Any
from datetime import datetime
from backend.ai.data_extractor import detect_rookie_signal, detect_expert_signal


def structure_order_behavior(profile: Dict, orders: List[Dict]) -> Dict[str, Any]:
    """
    将订单数据转换为结构化行为特征

    Args:
        profile: 客户档案数据
        orders: 订单列表

    Returns:
        {
            "购买特征": Dict,
            "售后行为": Dict,
            "沟通特征": Dict,
            "价值特征": Dict
        }
    """
    return {
        "购买特征": analyze_purchase_features(profile, orders),
        "售后行为": analyze_after_sales_behavior(profile, orders),
        "沟通特征": analyze_communication_pattern(profile),
        "价值特征": analyze_value_metrics(profile)
    }


def analyze_purchase_features(profile: Dict, orders: List[Dict]) -> Dict[str, Any]:
    """分析购买特征"""
    return {
        "首次购买品类": profile.get("top_category", "未知"),
        "品类集中度": calculate_category_focus(orders),
        "客单价趋势": calculate_price_trend(orders),
        "复购间隔": calculate_avg_interval(profile, orders),
        "首次购买时间": profile.get("first_purchase_date", ""),
        "最后购买时间": profile.get("last_purchase_date", ""),
        "总订单数": profile.get("total_orders", 0)
    }


def analyze_after_sales_behavior(profile: Dict, orders: List[Dict]) -> Dict[str, Any]:
    """分析售后行为"""
    # 计算退款率
    l6m_refund_rate = profile.get("l6m_refund_rate", 0) or 0
    total_refund_count = profile.get("total_refund_count", 0) or 0

    return {
        "退款率": f"{l6m_refund_rate:.1%}" if isinstance(l6m_refund_rate, (int, float)) else "0%",
        "退款次数": total_refund_count,
        "退货原因": analyze_refund_reasons(orders),
        "投诉次数": count_complaints(orders),
        "品质敏感度": judge_quality_sensitivity(l6m_refund_rate, total_refund_count)
    }


def analyze_communication_pattern(profile: Dict) -> Dict[str, Any]:
    """分析沟通特征"""
    chats = profile.get("chat_history", [])

    return {
        "主动咨询频率": profile.get("l3m_chat_frequency_days", 0),
        "沟通时机": analyze_communication_timing(profile),
        "问题类型分布": classify_chat_questions(chats),
        "语言风格": detect_language_style(chats),
        "新手信号数量": count_signals(chats, "rookie"),
        "专家信号数量": count_signals(chats, "expert")
    }


def analyze_value_metrics(profile: Dict) -> Dict[str, Any]:
    """分析价值特征"""
    l6m_netsales = profile.get("l6m_netsales", 0) or 0
    l1y_netsales = profile.get("l1y_netsales", 0) or 0
    historical_net_sales = profile.get("historical_net_sales", 0) or 0

    return {
        "VIP等级": profile.get("vip_level", "Non-VIP"),
        "L6M消费": f"¥{l6m_netsales:,.0f}",
        "L1Y消费": f"¥{l1y_netsales:,.0f}",
        "历史总消费": f"¥{historical_net_sales:,.0f}",
        "客单价": calculate_avg_order_price(profile),
        "消费趋势": calculate_consumption_trend(l6m_netsales, l1y_netsales)
    }


def calculate_category_focus(orders: List[Dict]) -> str:
    """
    计算品类集中度
    - 1个品类：专注型
    - 2个品类：偏好型
    - 3+品类：多样化
    """
    if not orders:
        return "未知"

    categories = set()
    for order in orders:
        category = order.get("category", order.get("commodity_name", ""))
        if category:
            # 简化品类名称（取主要品类）
            if "PIPES" in category.upper():
                categories.add("PIPES")
            elif "LIGHTER" in category.upper():
                categories.add("LIGHTER")
            elif "ACCESSORY" in category.upper():
                categories.add("ACCESSORY")
            else:
                categories.add("OTHER")

    if len(categories) == 0:
        return "未知"
    elif len(categories) == 1:
        return "专注型"
    elif len(categories) == 2:
        return "偏好型"
    else:
        return "多样化"


def calculate_price_trend(orders: List[Dict]) -> str:
    """
    分析客单价趋势
    """
    if not orders or len(orders) < 2:
        return "单次购买"

    # 提取所有订单的净销售额
    prices = []
    for order in orders:
        price = order.get("netsales", order.get("payment", 0))
        if price and price > 0:
            prices.append(price)

    if len(prices) < 2:
        return "单次购买"

    # 对比前半段和后半段的平均价格
    mid_point = len(prices) // 2
    first_half = prices[:mid_point]
    second_half = prices[mid_point:]

    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)

    if avg_second > avg_first * 1.2:
        return "上升"
    elif avg_second < avg_first * 0.8:
        return "下降"
    else:
        return "稳定"


def calculate_avg_interval(profile: Dict, orders: List[Dict]) -> str:
    """计算平均复购间隔"""
    first_purchase = profile.get("first_purchase_date")
    last_purchase = profile.get("last_purchase_date")
    total_orders = profile.get("total_orders", 0)

    if not first_purchase or not last_purchase or total_orders < 2:
        return "单次购买"

    try:
        # 计算购买天数跨度
        start = datetime.strptime(str(first_purchase)[:10], "%Y-%m-%d")
        end = datetime.strptime(str(last_purchase)[:10], "%Y-%m-%d")
        days_diff = (end - start).days

        if days_diff <= 0:
            return "单次购买"

        avg_days = days_diff / (total_orders - 1)

        if avg_days < 30:
            return f"{int(avg_days)}天（高频）"
        elif avg_days < 90:
            return f"{int(avg_days)}天（中频）"
        else:
            return f"{int(avg_days)}天（低频）"

    except Exception:
        return "未知"


def analyze_refund_reasons(orders: List[Dict]) -> str:
    """分析退款原因"""
    if not orders:
        return "无退款"

    refund_orders = [o for o in orders if o.get("refund_status") == "是"]

    if not refund_orders:
        return "无退款"

    # 这里可以根据实际情况分析退款原因
    # 暂时返回简单统计
    return f"{len(refund_orders)}次退款（品质要求高/不匹配等）"


def count_complaints(orders: List[Dict]) -> int:
    """统计投诉次数"""
    # 可以从聊天记录或订单备注中提取
    # 暂时返回0
    return 0


def judge_quality_sensitivity(refund_rate: float, refund_count: int) -> str:
    """判断品质敏感度"""
    if refund_rate > 0.1 or refund_count >= 3:
        return "高（对品质要求严格）"
    elif refund_rate > 0.05 or refund_count >= 1:
        return "中（有一定品质要求）"
    else:
        return "低（容易满足）"


def analyze_communication_timing(profile: Dict) -> str:
    """分析沟通时机"""
    # 可以分析聊天时间分布（工作日/周末，白天/晚上）
    # 暂时返回简单描述
    return "根据购买后咨询判断"


def classify_chat_questions(chats: List[Dict]) -> str:
    """分类聊天问题"""
    if not chats:
        return "无聊天记录"

    # 简单统计
    types = []
    for chat in chats:
        content = chat.get("content", "")

        if any(word in content for word in ["怎么用", "如何", "不懂"]):
            types.append("使用指导")
        elif any(word in content for word in ["推荐", "哪个好", "怎么选"]):
            types.append("寻求推荐")
        elif any(word in content for word in ["多少钱", "价格", "折扣"]):
            types.append("价格咨询")

    if not types:
        return "日常交流"

    # 返回最主要的类型
    from collections import Counter
    most_common = Counter(types).most_common(1)[0][0]
    return most_common


def detect_language_style(chats: List[Dict]) -> str:
    """
    检测客户语言风格
    - 新手口语：大量疑问句、语气词
    - 专业术语：使用行业术语
    - 日常交流：简单直接
    """
    if not chats:
        return "未知"

    question_count = 0
    term_count = 0

    for chat in chats:
        content = chat.get("content", "")

        if "？" in content or "?" in content:
            question_count += 1

        if any(term in content for term in EXPERT_SIGNALS_TERMS):
            term_count += 1

    # 专家信号关键词
    EXPERT_SIGNALS_TERMS = [
        "finish", "briar", "grain", "吸阻", "过滤",
        "产地", "工艺", "材质", "型号"
    ]

    if question_count / len(chats) > 0.5:
        return "新手口语"
    elif term_count / len(chats) > 0.3:
        return "专业术语"
    else:
        return "日常交流"


def count_signals(chats: List[Dict], signal_type: str) -> int:
    """统计信号数量"""
    if not chats:
        return 0

    count = 0
    for chat in chats:
        content = chat.get("content", "")

        if signal_type == "rookie":
            if detect_rookie_signal(content):
                count += 1
        elif signal_type == "expert":
            if detect_expert_signal(content):
                count += 1

    return count


def calculate_avg_order_price(profile: Dict) -> str:
    """计算客单价"""
    total_orders = profile.get("total_orders", 0)
    historical_net_sales = profile.get("historical_net_sales", 0) or 0

    if total_orders == 0:
        return "¥0"

    avg_price = historical_net_sales / total_orders
    return f"¥{avg_price:,.0f}"


def calculate_consumption_trend(l6m: float, l1y: float) -> str:
    """计算消费趋势"""
    if l6m == 0 or l1y == 0:
        return "稳定"

    # L6M是最近6个月，L1Y是最近1年
    # 如果L6M占L1Y比例超过50%，说明消费在上升
    ratio = l6m / l1y if l1y > 0 else 0

    if ratio > 0.6:
        return "上升（最近活跃）"
    elif ratio < 0.3:
        return "下降（活跃度降低）"
    else:
        return "稳定"
