-- ============================================
-- 获取高价值买家(L6M消费 > 阈值)
-- ============================================
-- 用途: 高价值客户识别
-- 性能: < 0.1秒(使用l6m_netsales索引)
-- ============================================

SELECT
    buyer_nick,
    channel,
    buyer_type,
    vip_level,
    client_monthly_tag,
    historical_net_sales,
    l6m_netsales,
    l6m_orders,
    l1y_netsales,
    total_orders,
    city,
    top_category,
    discount_sensitivity,
    last_purchase_date
FROM target_buyers_precomputed
WHERE l6m_netsales >= %s
ORDER BY l6m_netsales DESC
LIMIT %s OFFSET %s;
