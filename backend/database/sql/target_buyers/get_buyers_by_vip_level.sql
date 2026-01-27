-- ============================================
-- 按VIP等级筛选买家
-- ============================================
-- 用途: VIP分级管理
-- 性能: < 0.1秒(使用vip_level索引)
-- ============================================

SELECT
    buyer_nick,
    channel,
    buyer_type,
    vip_level,
    client_monthly_tag,
    rolling_24m_netsales,
    historical_net_sales,
    l1y_netsales,
    l6m_netsales,
    total_orders,
    city,
    top_category,
    second_category,
    discount_sensitivity,
    churn_risk,
    last_purchase_date,
    updated_at
FROM target_buyers_precomputed
WHERE vip_level = %s
ORDER BY rolling_24m_netsales DESC
LIMIT %s OFFSET %s;
