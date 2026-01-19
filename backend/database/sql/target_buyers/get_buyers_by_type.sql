-- ============================================
-- 按买家类型筛选(SMOKER/VIC/BOTH)
-- ============================================
-- 用途: Dashboard买家类型筛选
-- 性能: < 0.1秒(使用索引)
-- ============================================

SELECT
    buyer_nick,
    channel,
    buyer_type,
    vip_level,
    client_monthly_tag,
    historical_net_sales,
    l6m_spend,
    l6m_orders,
    city,
    top_category,
    churn_risk,
    last_purchase_date,
    last_chat_date
FROM target_buyers_precomputed
WHERE buyer_type = %s
ORDER BY l6m_spend DESC
LIMIT %s OFFSET %s;
