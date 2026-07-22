-- V2-first Priority List. Enabled only through AI_ANALYSIS_V2_PRIORITY_ENABLED.
SELECT
    tb.buyer_nick,
    tb.channel,
    tb.buyer_type,
    tb.vip_level,
    tb.rfm_segment,
    tb.follow_priority,
    tb.last_purchase_date,
    tb.last_chat_date,
    tb.l6m_netsales,
    tb.l1y_netsales,
    tb.l1y_refund_rate,
    tb.historical_net_sales,
    COALESCE(v2.current_sentiment_label, ai.sentiment_label, tb.sentiment_label) AS sentiment_label,
    COALESCE(ai.sentiment_score, tb.sentiment_score) AS sentiment_score,
    COALESCE(ai.dominant_intent, tb.dominant_intent) AS dominant_intent,
    v2.attention_priority,
    v2.primary_issue_code,
    v2.primary_issue_detail,
    v2.highest_severity,
    v2.active_issue_count,
    v2.recommended_action AS ai_v2_recommended_action,
    v2.last_event_at AS ai_v2_last_event_at,
    CASE WHEN tb.chat_frequency_days > 0 THEN TRUE ELSE FALSE END AS has_chat,
    tb.chat_frequency_days,
    CASE
        WHEN csl.status IN ('contacted', 'resolved') AND (
            v2.last_event_at > csl.updated_at
            OR EXISTS (SELECT 1 FROM dunhill_t01_trade_line t WHERE t.买家昵称 = tb.buyer_nick AND t.最后付款时间 > csl.updated_at AND t.退款金额 > 0)
            OR (v2.buyer_nick IS NULL AND EXISTS (SELECT 1 FROM buyer_ai_analysis_cache ai2 WHERE ai2.buyer_nick = tb.buyer_nick AND ai2.incremental_sentiment_label = 'Negative' AND ai2.incremental_chat_to_date > csl.updated_at))
            OR (tb.churn_risk = '高' AND NOT EXISTS (SELECT 1 FROM target_buyers_precomputed_history h WHERE h.buyer_nick = tb.buyer_nick AND h.snapshot_date = DATE(csl.updated_at) AND h.churn_risk = '高'))
            OR EXISTS (SELECT 1 FROM target_buyers_precomputed_history h_prev JOIN target_buyers_precomputed_history h_now ON h_prev.buyer_nick = h_now.buyer_nick WHERE h_prev.buyer_nick = tb.buyer_nick AND h_prev.snapshot_date = (SELECT MAX(snapshot_date) FROM target_buyers_precomputed_history WHERE buyer_nick = tb.buyer_nick AND snapshot_date <= DATE(csl.updated_at)) AND h_now.snapshot_date = (SELECT MAX(snapshot_date) FROM target_buyers_precomputed_history) AND h_prev.rfm_segment IN ('重要价值客户', '重要保持客户', '优质价值客户', '优质保持客户') AND h_now.rfm_segment IN ('潜力客户', '待激活客户', '已流失'))
        ) THEN 'pending'
        ELSE csl.status
    END AS service_status,
    csl.updated_at AS service_updated_at,
    csl.notes AS service_notes,
    ai.persona_key_interests,
    ai.persona_pain_points,
    ai.persona_recommended_action,
    ai.persona_summary,
    ai.persona_analyzed_at,
    ai.persona_analyzed_last_purchase_date,
    ai.persona_analyzed_last_chat_date,
    CASE
        WHEN ai.persona_summary IS NULL THEN TRUE
        WHEN tb.last_purchase_date IS NOT NULL AND (
            ai.persona_analyzed_last_purchase_date IS NULL
            OR tb.last_purchase_date > ai.persona_analyzed_last_purchase_date
        ) THEN TRUE
        WHEN tb.last_chat_date IS NOT NULL AND (
            ai.persona_analyzed_last_chat_date IS NULL
            OR tb.last_chat_date > ai.persona_analyzed_last_chat_date
        ) THEN TRUE
        ELSE FALSE
    END AS persona_refresh_required
FROM target_buyers_precomputed tb
LEFT JOIN ai_analysis_v2_customer_state v2 ON v2.buyer_nick = tb.buyer_nick
LEFT JOIN buyer_ai_analysis_cache ai ON ai.buyer_nick = tb.buyer_nick
LEFT JOIN customer_service_log csl ON csl.buyer_nick = tb.buyer_nick AND csl.workstream = 'priority'
WHERE 1=1
    [[AND tb.channel IN %(channel)s]]
    [[AND tb.buyer_type IN %(buyer_type)s]]
    [[AND tb.follow_priority IN %(follow_priority)s]]
    [[AND COALESCE(v2.current_sentiment_label, ai.sentiment_label, tb.sentiment_label) IN %(sentiment_label)s]]
    [[AND tb.chat_frequency_days > 0 AND %(has_chat)s = 'yes']]
    [[AND tb.chat_frequency_days = 0 AND %(has_chat)s = 'no']]
    [[AND (
        (csl.id IS NULL AND (tb.follow_priority IN ('紧急', '高') OR v2.attention_priority IN ('urgent', 'high') OR COALESCE(v2.current_sentiment_label, ai.sentiment_label, tb.sentiment_label) = 'Negative'))
        OR
        (csl.status = 'pending' AND (tb.follow_priority IN ('紧急', '高') OR v2.attention_priority IN ('urgent', 'high') OR COALESCE(v2.current_sentiment_label, ai.sentiment_label, tb.sentiment_label) = 'Negative'))
        OR
        (csl.status IN ('contacted', 'resolved') AND (
            v2.last_event_at > csl.updated_at
            OR EXISTS (SELECT 1 FROM dunhill_t01_trade_line t WHERE t.买家昵称 = tb.buyer_nick AND t.最后付款时间 > csl.updated_at AND t.退款金额 > 0)
            OR (v2.buyer_nick IS NULL AND EXISTS (SELECT 1 FROM buyer_ai_analysis_cache ai2 WHERE ai2.buyer_nick = tb.buyer_nick AND ai2.incremental_sentiment_label = 'Negative' AND ai2.incremental_chat_to_date > csl.updated_at))
            OR (tb.churn_risk = '高' AND NOT EXISTS (SELECT 1 FROM target_buyers_precomputed_history h WHERE h.buyer_nick = tb.buyer_nick AND h.snapshot_date = DATE(csl.updated_at) AND h.churn_risk = '高'))
            OR EXISTS (SELECT 1 FROM target_buyers_precomputed_history h_prev JOIN target_buyers_precomputed_history h_now ON h_prev.buyer_nick = h_now.buyer_nick WHERE h_prev.buyer_nick = tb.buyer_nick AND h_prev.snapshot_date = (SELECT MAX(snapshot_date) FROM target_buyers_precomputed_history WHERE buyer_nick = tb.buyer_nick AND snapshot_date <= DATE(csl.updated_at)) AND h_now.snapshot_date = (SELECT MAX(snapshot_date) FROM target_buyers_precomputed_history) AND h_prev.rfm_segment IN ('重要价值客户', '重要保持客户', '优质价值客户', '优质保持客户') AND h_now.rfm_segment IN ('潜力客户', '待激活客户', '已流失'))
        ))
    )]]
ORDER BY
    CASE COALESCE(v2.current_sentiment_label, ai.sentiment_label, tb.sentiment_label)
        WHEN 'Negative' THEN 1 WHEN 'Neutral' THEN 2 WHEN 'Positive' THEN 3 ELSE 4
    END,
    CASE v2.attention_priority
        WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 WHEN 'low' THEN 4 ELSE 5
    END,
    CASE tb.follow_priority
        WHEN '紧急' THEN 1 WHEN '高' THEN 2 WHEN '中' THEN 3 WHEN '低' THEN 4 ELSE 5
    END,
    tb.last_purchase_date DESC,
    tb.l6m_netsales DESC
LIMIT %(limit)s OFFSET %(offset)s;
