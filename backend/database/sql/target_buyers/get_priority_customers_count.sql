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
WHERE 1=1
    -- 动态筛选条件 (筛选时也优先使用缓存表的实时数据)
    [[AND tb.channel IN %(channel)s]]
    [[AND tb.buyer_type IN %(buyer_type)s]]
    [[AND tb.follow_priority IN %(follow_priority)s]]
    [[AND COALESCE(ai.sentiment_label, tb.sentiment_label) IN %(sentiment_label)s]]
    [[AND tb.chat_frequency_days > 0 AND %(has_chat)s = 'yes']]
    [[AND tb.chat_frequency_days = 0 AND %(has_chat)s = 'no']]
    -- 默认筛选逻辑
    [[AND (tb.follow_priority IN ('紧急', '高') OR COALESCE(ai.sentiment_label, tb.sentiment_label) = 'Negative')]];
