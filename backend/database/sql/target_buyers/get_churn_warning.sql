-- ============================================
-- 流失预警列表 (Round 2)
-- ============================================
-- 用途: PriorityAttentionBoard Tab 2 "流失预警"
-- 逻辑 (3 个 OR 入选条件):
--   A. segment 退化: 30D 前好 segment, 现在变差 (含严重程度: cond_a_severe)
--   B. churn_risk 升级: 低/中 → 高
--   C. l6m_netsales 坍塌: 30D 前 >= 1万, 现在下降 >= 50 percent
-- 参数: limit, offset
-- ============================================
--
-- 重要: snapshot 日期用 MAX(snapshot_date) 而不是 CURDATE()
-- 原因: MySQL event snapshot_target_buyers_history 是第二天 13:30 触发
--       (见 snapshot_target_buyers_history.sql line 460-465)
--       用 CURDATE() 会导致今天没 snapshot 时整个 JOIN 返回 0 行
-- h_prev fallback: 30D 前没 snapshot 就用最老的 (graceful degradation)

SELECT
    h_now.buyer_nick,
    tb.channel,
    tb.buyer_type,
    tb.vip_level,
    h_now.rfm_segment_prev AS segment_30d_ago,
    h_now.rfm_segment AS segment_now,
    h_now.churn_risk_prev AS churn_risk_30d_ago,
    h_now.churn_risk AS churn_risk_now,
    ROUND(h_now.l6m_netsales - h_now.l6m_netsales_prev, 2) AS l6m_netsales_change,
    ROUND(
        (h_now.l6m_netsales - h_now.l6m_netsales_prev)
        / NULLIF(h_now.l6m_netsales_prev, 0) * 100,
    1) AS l6m_change_pct,
    tb.last_purchase_date,
    tb.last_chat_date,
    -- 入选原因 (可多个, 逗号分隔; 前端按 , 拆分渲染多个 tag)
    TRIM(BOTH ',' FROM CONCAT_WS(',',
        IF(_cond_a, 'segment退化', NULL),
        IF(_cond_b, 'churn高风险', NULL),
        IF(_cond_c, '购买力坍塌', NULL)
    )) AS selection_reasons,
    -- 严重程度档位 (1=最严重, 4=最轻)
    CASE
        WHEN _cond_a_severe THEN 1
        WHEN _cond_b AND NOT _cond_c THEN 2
        WHEN _cond_a AND NOT _cond_b AND NOT _cond_c THEN 2
        WHEN _cond_c THEN 3
        WHEN _cond_a THEN 3
        ELSE 4
    END AS severity_tier
FROM (
    -- 内层把 3 个条件作为"派生列"算好, 避免外层到处重复
    SELECT
        h_now_inner.buyer_nick,
        h_now_inner.rfm_segment,
        h_now_inner.churn_risk,
        h_now_inner.l6m_netsales,
        h_prev_inner.rfm_segment AS rfm_segment_prev,
        h_prev_inner.churn_risk AS churn_risk_prev,
        h_prev_inner.l6m_netsales AS l6m_netsales_prev,
        -- 严重退化: 重要价值/保持 → 已流失/低价值
        (h_prev_inner.rfm_segment IN ('重要价值客户', '重要保持客户')
         AND h_now_inner.rfm_segment IN ('已流失', '低价值客户')) AS _cond_a_severe,
        -- 段位退化: 任何好 segment → 任何差 segment
        ((h_prev_inner.rfm_segment IN ('重要价值客户', '重要保持客户', '重要发展客户',
                                       '优质价值客户', '优质保持客户', '优质发展客户'))
         AND (h_now_inner.rfm_segment IN ('潜力客户', '待激活客户', '已流失', '低价值客户',
                                          '重要挽留客户', '优质挽留客户'))) AS _cond_a,
        -- churn 升级: 低/中 → 高
        (h_prev_inner.churn_risk IN ('低', '中') AND h_now_inner.churn_risk = '高') AS _cond_b,
        -- 购买力坍塌: l6m 30D 下降 >= 50 percent 且 30D 前 >= 1万
        (h_prev_inner.l6m_netsales >= 10000
         AND (h_now_inner.l6m_netsales - h_prev_inner.l6m_netsales) <= -0.5 * h_prev_inner.l6m_netsales) AS _cond_c
    FROM target_buyers_precomputed_history h_now_inner
    JOIN target_buyers_precomputed_history h_prev_inner
        ON h_now_inner.buyer_nick = h_prev_inner.buyer_nick
        AND h_prev_inner.snapshot_date = (
            SELECT COALESCE(
                (SELECT MAX(snapshot_date) FROM target_buyers_precomputed_history
                    WHERE snapshot_date <= DATE_SUB(
                        (SELECT MAX(snapshot_date) FROM target_buyers_precomputed_history),
                        INTERVAL 30 DAY
                    )),
                (SELECT MIN(snapshot_date) FROM target_buyers_precomputed_history)
            )
        )
    WHERE h_now_inner.snapshot_date = (SELECT MAX(snapshot_date) FROM target_buyers_precomputed_history)
) AS h_now
JOIN target_buyers_precomputed tb
    ON h_now.buyer_nick = tb.buyer_nick
WHERE h_now._cond_a OR h_now._cond_b OR h_now._cond_c
ORDER BY severity_tier ASC,
         (h_now.l6m_netsales - h_now.l6m_netsales_prev) ASC,
         tb.last_purchase_date DESC
LIMIT %(limit)s OFFSET %(offset)s
