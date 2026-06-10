-- ============================================
-- 获取优先关注客户列表(带AI画像)
-- ============================================
-- 用途: Overview页面PriorityAttentionBoard组件
-- 性能: < 1秒 (JOIN + 索引查询)
-- 参数: channel, buyer_type, follow_priority, has_chat, limit, offset
-- 默认筛选: follow_priority IN ('紧急', '高') OR sentiment_label = 'Negative'
-- 更新: 2026-03-19 情感/意图优先从缓存表获取(实时更新)
-- ============================================

SELECT
    -- 基本信息字段
    tb.buyer_nick,
    tb.channel,
    tb.buyer_type,
    tb.vip_level,
    tb.rfm_segment,
    tb.follow_priority,
    tb.last_purchase_date,
    tb.last_chat_date,

    -- 消费指标
    tb.l6m_netsales,
    tb.l1y_netsales,
    tb.l1y_refund_rate,
    tb.historical_net_sales,

    -- 情感/意图 (优先从缓存表获取，缓存无数据则使用预计算表)
    COALESCE(ai.sentiment_label, tb.sentiment_label) AS sentiment_label,
    COALESCE(ai.sentiment_score, tb.sentiment_score) AS sentiment_score,
    COALESCE(ai.dominant_intent, tb.dominant_intent) AS dominant_intent,

    -- 聊天状态
    CASE WHEN tb.chat_frequency_days > 0 THEN TRUE ELSE FALSE END AS has_chat,
    tb.chat_frequency_days,

    -- 客服处理记录 (Round 1)
    csl.status AS service_status,
    csl.updated_at AS service_updated_at,
    csl.notes AS service_notes,

    -- AI画像分析 (从缓存表LEFT JOIN)
    ai.persona_key_interests,
    ai.persona_pain_points,
    ai.persona_recommended_action,
    ai.persona_summary,
    ai.persona_analyzed_at,
    ai.persona_analyzed_last_purchase_date,
    ai.persona_analyzed_last_chat_date,
    CASE
        WHEN ai.persona_summary IS NULL THEN TRUE
        WHEN (tb.last_purchase_date IS NOT NULL AND (
            ai.persona_analyzed_last_purchase_date IS NULL
            OR tb.last_purchase_date > ai.persona_analyzed_last_purchase_date
        )) THEN TRUE
        WHEN (tb.last_chat_date IS NOT NULL AND (
            ai.persona_analyzed_last_chat_date IS NULL
            OR tb.last_chat_date > ai.persona_analyzed_last_chat_date
        )) THEN TRUE
        ELSE FALSE
    END AS persona_refresh_required

FROM target_buyers_precomputed tb
LEFT JOIN buyer_ai_analysis_cache ai ON tb.buyer_nick = ai.buyer_nick
LEFT JOIN customer_service_log csl ON tb.buyer_nick = csl.buyer_nick
WHERE 1=1
    -- 动态筛选条件 (筛选时也优先使用缓存表的实时数据)
    [[AND tb.channel IN %(channel)s]]
    [[AND tb.buyer_type IN %(buyer_type)s]]
    [[AND tb.follow_priority IN %(follow_priority)s]]
    [[AND COALESCE(ai.sentiment_label, tb.sentiment_label) IN %(sentiment_label)s]]
    [[AND tb.chat_frequency_days > 0 AND %(has_chat)s = 'yes']]
    [[AND tb.chat_frequency_days = 0 AND %(has_chat)s = 'no']]
    -- 默认筛选逻辑 (当 use_default_filter = true 时)
    -- 条件 A: 从未处理 → 现有逻辑
    -- 条件 B: 处理过 → Rolling Window 重评估 (即时事件 + 累计退化)
    [[AND (
        (csl.id IS NULL AND (tb.follow_priority IN ('紧急', '高') OR COALESCE(ai.sentiment_label, tb.sentiment_label) = 'Negative'))
        OR
        (csl.status IN ('contacted', 'resolved') AND (
            EXISTS (SELECT 1 FROM dunhill_t01_trade_line t WHERE t.买家昵称 = tb.buyer_nick AND t.最后付款时间 > csl.updated_at AND t.退款金额 > 0)
            OR EXISTS (SELECT 1 FROM chat_history ch JOIN buyer_ai_analysis_cache ai2 ON ch.id = ai2.chat_id WHERE ch.user_nick = tb.buyer_nick AND ch.msg_time > csl.updated_at AND ai2.sentiment_label = 'Negative')
            OR (tb.churn_risk = '高' AND NOT EXISTS (SELECT 1 FROM target_buyers_precomputed_history h WHERE h.buyer_nick = tb.buyer_nick AND h.snapshot_date = DATE(csl.updated_at) AND h.churn_risk = '高'))
            OR EXISTS (SELECT 1 FROM target_buyers_precomputed_history h_prev JOIN target_buyers_precomputed_history h_now ON h_prev.buyer_nick = h_now.buyer_nick WHERE h_prev.buyer_nick = tb.buyer_nick AND h_prev.snapshot_date = (SELECT MAX(snapshot_date) FROM target_buyers_precomputed_history WHERE buyer_nick = tb.buyer_nick AND snapshot_date <= DATE(csl.updated_at)) AND h_now.snapshot_date = CURDATE() AND h_prev.rfm_segment IN ('重要价值客户', '重要保持客户', '优质价值客户', '优质保持客户') AND h_now.rfm_segment IN ('潜力客户', '待激活客户', '已流失'))
        ))
    )]]
ORDER BY
    -- 1. 按情感排序: Negative优先 (使用缓存实时数据)
    CASE COALESCE(ai.sentiment_label, tb.sentiment_label)
        WHEN 'Negative' THEN 1
        WHEN 'Neutral' THEN 2
        WHEN 'Positive' THEN 3
        ELSE 4
    END,
    -- 2. 按优先级排序: 紧急 > 高 > 中 > 低
    CASE tb.follow_priority
        WHEN '紧急' THEN 1
        WHEN '高' THEN 2
        WHEN '中' THEN 3
        WHEN '低' THEN 4
        ELSE 5
    END,
    -- 3. 按最后购买日期排序: 最近购买的优先
    tb.last_purchase_date DESC,
    -- 4. 按L6M消费金额
    tb.l6m_netsales DESC
LIMIT %(limit)s OFFSET %(offset)s;
