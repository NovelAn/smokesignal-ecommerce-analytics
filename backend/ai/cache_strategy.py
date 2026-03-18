"""
Cache Strategy - 分层缓存策略
根据客户特征动态调整缓存TTL，优化性能和成本
"""
from enum import Enum
from typing import Dict, Any


class CacheTier(Enum):
    """缓存层级"""
    HOT = 7    # VIP客户 (V3/V2) - 7天TTL（高频访问）
    WARM = 14  # 有聊天记录 - 14天TTL
    COLD = 30  # 无聊天记录 - 30天TTL（数据变化慢）


def get_cache_tier(
    profile: Dict[str, Any],
    chat_count: int,
    l6m_netsales: float = 0
) -> CacheTier:
    """
    根据客户特征确定缓存层级

    策略:
    1. HOT (7天): V3/V2客户，或L6M消费 >= 150K
    2. WARM (14天): 有聊天记录（数据会变化）
    3. COLD (30天): 无聊天记录（仅消费数据，变化慢）

    Args:
        profile: 客户档案
        chat_count: 聊天记录数量
        l6m_netsales: 近6个月消费金额

    Returns:
        CacheTier枚举值
    """
    vip_level = profile.get("vip_level", "Non-VIP")

    # HOT: 高价值VIP客户
    if vip_level in ["V3", "V2"]:
        return CacheTier.HOT

    # HOT: 高消费客户（L6M >= 150K）
    if l6m_netsales >= 150000:
        return CacheTier.HOT

    # WARM: 有聊天记录（聊天内容会变化）
    if chat_count > 0:
        return CacheTier.WARM

    # COLD: 无聊天记录（仅消费数据）
    return CacheTier.COLD


def get_cache_ttl_days(tier: CacheTier) -> int:
    """
    获取缓存TTL（天数）

    Args:
        tier: 缓存层级

    Returns:
        TTL天数
    """
    return tier.value


def estimate_cache_hit_rate(
    total_buyers: int,
    hot_percentage: float = 0.1,
    warm_percentage: float = 0.3
) -> Dict[str, Any]:
    """
    估算缓存命中率

    Args:
        total_buyers: 总买家数
        hot_percentage: HOT层比例（默认10%）
        warm_percentage: WARM层比例（默认30%）

    Returns:
        {
            "hot_buyers": int,
            "warm_buyers": int,
            "cold_buyers": int,
            "estimated_hit_rate": float
        }
    """
    hot_buyers = int(total_buyers * hot_percentage)
    warm_buyers = int(total_buyers * warm_percentage)
    cold_buyers = total_buyers - hot_buyers - warm_buyers

    # 假设:
    # HOT: 90% 命中率（7天内重复查询）
    # WARM: 70% 命中率（14天内重复查询）
    # COLD: 50% 命中率（30天内重复查询）

    weighted_hit_rate = (
        hot_buyers * 0.9 +
        warm_buyers * 0.7 +
        cold_buyers * 0.5
    ) / total_buyers

    return {
        "hot_buyers": hot_buyers,
        "warm_buyers": warm_buyers,
        "cold_buyers": cold_buyers,
        "estimated_hit_rate": round(weighted_hit_rate * 100, 2)
    }


def calculate_cost_savings_with_cache(
    daily_analyses: int,
    cache_hit_rate: float,
    avg_cost_per_analysis: float = 7.0
) -> Dict[str, Any]:
    """
    计算缓存带来的成本节省

    Args:
        daily_analyses: 每日分析数量
        cache_hit_rate: 缓存命中率（0-1）
        avg_cost_per_analysis: 平均每次分析成本（元）

    Returns:
        {
            "daily_cost_without_cache": float,
            "daily_cost_with_cache": float,
            "daily_savings": float,
            "monthly_savings": float,
            "savings_percentage": float
        }
    """
    daily_cost_without_cache = daily_analyses * avg_cost_per_analysis
    daily_cache_hits = daily_analyses * cache_hit_rate
    daily_cost_with_cache = (daily_analyses - daily_cache_hits) * avg_cost_per_analysis

    daily_savings = daily_cost_without_cache - daily_cost_with_cache
    monthly_savings = daily_savings * 30
    savings_percentage = (daily_savings / daily_cost_without_cache) * 100 if daily_cost_without_cache > 0 else 0

    return {
        "daily_cost_without_cache": round(daily_cost_without_cache, 2),
        "daily_cost_with_cache": round(daily_cost_with_cache, 2),
        "daily_savings": round(daily_savings, 2),
        "monthly_savings": round(monthly_savings, 2),
        "savings_percentage": round(savings_percentage, 2)
    }


# 示例使用
if __name__ == "__main__":
    # 示例1: 确定缓存层级
    profile = {
        "vip_level": "V3",
        "l6m_netsales": 200000
    }
    tier = get_cache_tier(profile, chat_count=15)
    print(f"缓存层级: {tier.name}, TTL: {tier.value}天")

    # 示例2: 估算缓存命中率
    hit_rate = estimate_cache_hit_rate(total_buyers=1000)
    print(f"\n估算缓存命中率: {hit_rate}")

    # 示例3: 计算成本节省
    savings = calculate_cost_savings_with_cache(
        daily_analyses=100,
        cache_hit_rate=0.72,
        avg_cost_per_analysis=7.0
    )
    print(f"\n成本节省: {savings}")
