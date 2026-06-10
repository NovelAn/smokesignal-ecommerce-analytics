-- ============================================
-- VIP 等级趋势 (历史快照)
-- ============================================
-- 用途: 5 类 VIP 等级 (V0/V1/V2/V3/Non-VIP) 每日分布 + Net Sales
--       看 VIP 客户结构变化 (高端化趋势)
-- 参数: date_from, date_to (DATE)
-- 性能: idx_snapshot_vip (snapshot_date, vip_level)
-- ============================================

SELECT
    snapshot_date,
    vip_level,
    COUNT(*) AS customer_count,
    SUM(historical_net_sales) AS total_net_sales
FROM target_buyers_precomputed_history
WHERE snapshot_date BETWEEN %s AND %s
GROUP BY snapshot_date, vip_level
ORDER BY snapshot_date,
    CASE vip_level WHEN 'V3' THEN 5 WHEN 'V2' THEN 4 WHEN 'V1' THEN 3 WHEN 'V0' THEN 2 ELSE 1 END DESC
