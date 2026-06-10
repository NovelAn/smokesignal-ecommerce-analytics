-- ============================================
-- 池子汇总趋势 (历史快照)
-- ============================================
-- 用途: dashboard 池子大小变化趋势
-- 参数: date_from, date_to (DATE)
-- 性能: idx_snapshot_date (B-tree)
-- 分区裁剪: 按月 RANGE PARTITION 自动
-- ============================================

SELECT
    snapshot_date,
    COUNT(*) AS pool_size,
    SUM(CASE WHEN is_smoker THEN 1 ELSE 0 END) AS smoker_count,
    SUM(CASE WHEN is_vic THEN 1 ELSE 0 END) AS vic_count,
    SUM(CASE WHEN buyer_type = 'BOTH' THEN 1 ELSE 0 END) AS both_count,
    SUM(CASE WHEN client_monthly_tag = 'new' THEN 1 ELSE 0 END) AS new_count,
    SUM(CASE WHEN client_monthly_tag = 'active_old' THEN 1 ELSE 0 END) AS active_old_count,
    SUM(CASE WHEN client_monthly_tag = 'recall_old' THEN 1 ELSE 0 END) AS recall_old_count,
    SUM(historical_gmv) AS total_gmv,
    SUM(historical_net_sales) AS total_net_sales
FROM target_buyers_precomputed_history
WHERE snapshot_date BETWEEN %s AND %s
GROUP BY snapshot_date
ORDER BY snapshot_date
