-- ============================================
-- Segment 趋势 (历史快照)
-- ============================================
-- 用途: 13 类 RFM segment 每日分布 (dashboard 趋势图)
--       Negative 客户趋势: filter segment='已流失' 或 '重要挽留客户'
-- 参数: date_from, date_to (DATE), segment (可选 VARCHAR)
-- 性能: idx_snapshot_date 索引 + 按月分区裁剪
-- ============================================

SELECT
    snapshot_date,
    rfm_segment,
    COUNT(*) AS customer_count
FROM target_buyers_precomputed_history
WHERE snapshot_date BETWEEN %s AND %s
  AND (%s IS NULL OR rfm_segment = %s)
GROUP BY snapshot_date, rfm_segment
ORDER BY snapshot_date, rfm_segment
