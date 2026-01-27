-- ============================================
-- 获取流失风险高的买家
-- ============================================
-- 用途: 流失风险预警Dashboard
-- 性能: < 0.1秒(使用churn_risk索引)
-- ============================================

SELECT
    buyer_nick,
    channel,
    buyer_type,
    vip_level,
    client_monthly_tag,
    historical_net_sales,
    l6m_netsales,
    city,
    top_category,
    churn_risk,
    last_purchase_date,
    last_chat_date,
    DATEDIFF(NOW(), last_purchase_date) as days_since_last_purchase,
    DATEDIFF(NOW(), last_chat_date) as days_since_last_chat
FROM target_buyers_precomputed
WHERE churn_risk = %s
ORDER BY
    CASE churn_risk
        WHEN '高' THEN 1
        WHEN '中' THEN 2
        ELSE 3
    END,
    last_purchase_date ASC
LIMIT %s OFFSET %s;
