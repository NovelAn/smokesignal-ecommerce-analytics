-- ============================================
-- 获取Smoker买家列表(按消费金额排序)
-- ============================================
-- 用途: Smoker客户管理
-- 性能: < 0.1秒(使用buyer_type和l6m_spend索引)
-- ============================================

SELECT
    buyer_nick,
    channel,
    buyer_type,
    vip_level,
    client_monthly_tag,
    top_category,
    second_category,
    third_category,
    historical_net_sales,
    l6m_spend,
    l6m_orders,
    l1y_spend,
    total_orders,
    city,
    discount_sensitivity,
    churn_risk,
    last_purchase_date,
    last_chat_date
FROM target_buyers_precomputed
WHERE is_smoker = TRUE
ORDER BY l6m_spend DESC
LIMIT %s OFFSET %s;
