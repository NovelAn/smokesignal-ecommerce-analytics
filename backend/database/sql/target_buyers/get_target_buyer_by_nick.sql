-- ============================================
-- 根据买家昵称获取详细信息
-- ============================================
-- 用途: 买家360°详情页
-- 性能: < 0.1秒(主键查询)
-- 更新: 2026-03-17 JOIN buyer_ai_analysis_cache获取intent_distribution
-- ============================================

SELECT
    tb.buyer_nick,
    tb.channel,
    tb.buyer_type,
    tb.is_smoker,
    tb.is_vic,
    tb.vip_level,
    tb.client_monthly_tag,

    -- 历史指标
    tb.historical_gmv,
    tb.historical_refund,
    tb.historical_net_sales,
    tb.total_orders,
    tb.total_net_orders,
    tb.refund_rate,
    tb.first_purchase_date,
    tb.last_purchase_date,

    -- Rolling 24个月
    tb.rolling_24m_gmv,
    tb.rolling_24m_netsales,
    tb.rolling_24m_orders,
    tb.rolling_24m_net_orders,

    -- L6M指标
    tb.l6m_netsales,
    tb.l6m_gmv,
    tb.l6m_orders,
    tb.l6m_refund_rate,

    -- L1Y指标
    tb.l1y_netsales,
    tb.l1y_gmv,
    tb.l1y_orders,
    tb.l1y_refund_rate,

    -- 折扣敏感度
    tb.discount_ratio,
    tb.discount_sensitivity,

    -- 聊天指标
    tb.chat_frequency_days,
    tb.total_chat_messages,
    tb.first_chat_date,
    tb.last_chat_date,
    tb.l30d_chat_frequency_days,
    tb.l3m_chat_frequency_days,
    tb.avg_chat_interval_days,

    -- 流失风险
    tb.churn_risk,

    -- 地理位置
    tb.city,

    -- 品类偏好
    tb.top_category,
    tb.second_category,
    tb.third_category,

    -- RFM分层
    tb.rfm_recency_score,
    tb.rfm_frequency_score,
    tb.rfm_monetary_score,
    tb.rfm_segment,

    -- 情绪与意图
    tb.sentiment_label,
    tb.sentiment_score,
    tb.dominant_intent,
    tb.pre_sale_score,
    tb.post_sale_score,
    tb.complaint_tendency,

    -- 运营标签
    tb.follow_priority,

    -- 元数据
    tb.updated_at,

    -- AI分析缓存字段
    cache.intent_distribution,
    cache.dominant_intent as ai_dominant_intent,
    cache.sentiment_score as ai_sentiment_score,
    cache.sentiment_label as ai_sentiment_label

FROM target_buyers_precomputed tb
LEFT JOIN buyer_ai_analysis_cache cache ON tb.buyer_nick = cache.buyer_nick
WHERE tb.buyer_nick = %s;
