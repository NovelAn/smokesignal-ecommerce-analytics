-- ============================================
-- 获取VIC买家列表(按VIP等级排序)
-- ============================================
-- 用途: VIP客户管理
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
    discount_sensitivity,
    churn_risk,
    last_purchase_date
FROM target_buyers_precomputed
WHERE is_vic = TRUE
ORDER BY
    CASE vip_level
        WHEN 'V3' THEN 5
        WHEN 'V2' THEN 4
        WHEN 'V1' THEN 3
        WHEN 'V0' THEN 2
        ELSE 1
    END DESC,
    rolling_24m_netsales DESC
LIMIT %s OFFSET %s;
