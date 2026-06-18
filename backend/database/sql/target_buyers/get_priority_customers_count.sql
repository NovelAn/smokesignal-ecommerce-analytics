-- ============================================
-- 获取优先关注客户数量
-- ============================================
-- 用途: 分页总数查询
-- 参数: channel, buyer_type, follow_priority, has_chat
-- 更新: 2026-03-19 情感筛选优先使用缓存表实时数据
-- ============================================

SELECT COUNT(*) as total
FROM target_buyers_precomputed tb
LEFT JOIN buyer_ai_analysis_cache ai ON tb.buyer_nick = ai.buyer_nick
LEFT JOIN customer_service_log csl ON tb.buyer_nick = csl.buyer_nick AND csl.workstream = 'priority'
WHERE 1=1
    -- 动态筛选条件 (筛选时也优先使用缓存表的实时数据)
    [[AND tb.channel IN %(channel)s]]
    [[AND tb.buyer_type IN %(buyer_type)s]]
    [[AND tb.follow_priority IN %(follow_priority)s]]
    [[AND COALESCE(ai.sentiment_label, tb.sentiment_label) IN %(sentiment_label)s]]
    [[AND tb.chat_frequency_days > 0 AND %(has_chat)s = 'yes']]
    [[AND tb.chat_frequency_days = 0 AND %(has_chat)s = 'no']]
    -- 默认筛选逻辑：必须与 get_priority_customers.sql 完全一致
    [[AND (
        (csl.id IS NULL AND (tb.follow_priority IN ('紧急', '高') OR COALESCE(ai.sentiment_label, tb.sentiment_label) = 'Negative'))
        OR
        (csl.status = 'pending' AND (tb.follow_priority IN ('紧急', '高') OR COALESCE(ai.sentiment_label, tb.sentiment_label) = 'Negative'))
        OR
        (csl.status IN ('contacted', 'resolved') AND (
            EXISTS (SELECT 1 FROM dunhill_t01_trade_line t WHERE t.买家昵称 = tb.buyer_nick AND t.最后付款时间 > csl.updated_at AND t.退款金额 > 0)
            OR EXISTS (SELECT 1 FROM buyer_ai_analysis_cache ai2 WHERE ai2.buyer_nick = tb.buyer_nick AND ai2.incremental_sentiment_label = 'Negative' AND ai2.incremental_chat_to_date > csl.updated_at)
            OR (tb.churn_risk = '高' AND NOT EXISTS (SELECT 1 FROM target_buyers_precomputed_history h WHERE h.buyer_nick = tb.buyer_nick AND h.snapshot_date = DATE(csl.updated_at) AND h.churn_risk = '高'))
            OR EXISTS (SELECT 1 FROM target_buyers_precomputed_history h_prev JOIN target_buyers_precomputed_history h_now ON h_prev.buyer_nick = h_now.buyer_nick WHERE h_prev.buyer_nick = tb.buyer_nick AND h_prev.snapshot_date = (SELECT MAX(snapshot_date) FROM target_buyers_precomputed_history WHERE buyer_nick = tb.buyer_nick AND snapshot_date <= DATE(csl.updated_at)) AND h_now.snapshot_date = (SELECT MAX(snapshot_date) FROM target_buyers_precomputed_history) AND h_prev.rfm_segment IN ('重要价值客户', '重要保持客户', '优质价值客户', '优质保持客户') AND h_now.rfm_segment IN ('潜力客户', '待激活客户', '已流失'))
        ))
    )]];
