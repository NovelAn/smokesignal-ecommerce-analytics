-- ============================================
-- 流失预警列表 (Round 1)
-- ============================================
-- 用途: PriorityAttentionBoard Tab 2 "流失预警"
-- 逻辑: segment 退化 (30D 前 vs 现在) + churn_risk 上升
-- 参数: limit, offset
-- ============================================

SELECT
    h_now.buyer_nick,
    tb.channel,
    tb.buyer_type,
    tb.vip_level,
    h_prev.rfm_segment AS segment_30d_ago,
    h_now.rfm_segment AS segment_now,
    h_prev.churn_risk AS churn_risk_30d_ago,
    h_now.churn_risk AS churn_risk_now,
    ROUND(h_now.l6m_netsales - h_prev.l6m_netsales, 2) AS l6m_netsales_change,
    tb.last_purchase_date,
    tb.last_chat_date
FROM target_buyers_precomputed_history h_now
JOIN target_buyers_precomputed_history h_prev
    ON h_now.buyer_nick = h_prev.buyer_nick
    AND h_prev.snapshot_date = DATE_SUB(CURDATE(), INTERVAL 30 DAY)
JOIN target_buyers_precomputed tb
    ON h_now.buyer_nick = tb.buyer_nick
WHERE h_now.snapshot_date = CURDATE()
  AND (
    -- segment 退化: 之前是好 segment, 现在变差
    (h_prev.rfm_segment IN ('重要价值客户', '重要保持客户', '重要发展客户',
                             '优质价值客户', '优质保持客户', '优质发展客户')
     AND h_now.rfm_segment IN ('潜力客户', '待激活客户', '已流失', '低价值客户', '重要挽留客户', '优质挽留客户'))
    OR
    -- churn_risk 上升: 低/中 → 高
    (h_prev.churn_risk IN ('低', '中') AND h_now.churn_risk = '高')
  )
ORDER BY
    CASE
        WHEN h_prev.rfm_segment IN ('重要价值客户', '重要保持客户') AND h_now.rfm_segment IN ('已流失', '低价值客户') THEN 1
        WHEN h_now.churn_risk = '高' THEN 2
        ELSE 3
    END,
    h_now.l6m_netsales - h_prev.l6m_netsales ASC,
    tb.last_purchase_date DESC
LIMIT %(limit)s OFFSET %(offset)s
