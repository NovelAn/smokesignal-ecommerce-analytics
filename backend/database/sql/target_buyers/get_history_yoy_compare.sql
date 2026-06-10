-- ============================================
-- 同期对比 (历史快照) - YoY / MoM / 任意两日对比
-- ============================================
-- 用途: VIC YoY 对比, 同期对比, 月度环比
-- 参数: from_date, to_date (DATE) - 两个日期对比
-- 性能: PK (buyer_nick, snapshot_date) - 按日期直接 PK 查找
-- 分区裁剪: 按月 RANGE PARTITION 自动
-- ============================================

SELECT
    snapshot_date,
    COUNT(*) AS pool_size,
    SUM(CASE WHEN is_smoker THEN 1 ELSE 0 END) AS smoker_count,
    SUM(CASE WHEN is_vic THEN 1 ELSE 0 END) AS vic_count,
    SUM(CASE WHEN buyer_type = 'BOTH' THEN 1 ELSE 0 END) AS both_count,
    SUM(CASE WHEN is_vic AND vip_level = 'V3' THEN 1 ELSE 0 END) AS v3_count,
    SUM(CASE WHEN is_vic AND vip_level = 'V2' THEN 1 ELSE 0 END) AS v2_count,
    SUM(CASE WHEN is_vic AND vip_level = 'V1' THEN 1 ELSE 0 END) AS v1_count,
    SUM(CASE WHEN is_vic AND vip_level = 'V0' THEN 1 ELSE 0 END) AS v0_count,
    SUM(historical_net_sales) AS total_net_sales,
    SUM(rolling_24m_netsales) AS rolling_24m_total
FROM target_buyers_precomputed_history
WHERE snapshot_date IN (%s, %s)
GROUP BY snapshot_date
ORDER BY snapshot_date
