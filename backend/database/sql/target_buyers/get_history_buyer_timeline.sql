-- ============================================
-- 单买家历史时间线 (历史快照)
-- ============================================
-- 用途: 单买家跨时间所有关键指标
--       看 segment/VIP/GMV 随时间变化轨迹
-- 参数: buyer_nick (VARCHAR), date_from, date_to (DATE)
-- 性能: PK (buyer_nick, snapshot_date) - 索引覆盖
-- 返回: 每天一行 (该买家的 snapshot)
-- ============================================

SELECT
    snapshot_date,
    channel,
    is_smoker,
    is_vic,
    buyer_type,
    vip_level,
    client_monthly_tag,
    historical_net_sales,
    rolling_24m_netsales,
    l6m_netsales,
    l1y_netsales,
    total_orders,
    last_purchase_date,
    rfm_segment,
    churn_risk,
    top_category,
    discount_sensitivity
FROM target_buyers_precomputed_history
WHERE buyer_nick = %s
  AND snapshot_date BETWEEN %s AND %s
ORDER BY snapshot_date
