-- ============================================
-- 根据买家昵称获取详细信息
-- ============================================
-- 用途: 买家360°详情页
-- 性能: < 0.1秒(主键查询)
-- ============================================

SELECT
    buyer_nick,
    channel,
    buyer_type,
    is_smoker,
    is_vic,
    vip_level,
    client_monthly_tag,

    -- 历史指标
    historical_gmv,
    historical_refund,
    historical_net_sales,
    total_orders,
    total_net_orders,
    refund_rate,
    first_purchase_date,
    last_purchase_date,

    -- Rolling 24个月
    rolling_24m_netsales,
    rolling_24m_orders,

    -- L6M指标
    l6m_gmv,
    l6m_netsales,
    l6m_orders,
    l6m_refund_rate,

    -- L1Y指标
    l1y_gmv,
    l1y_netsales,
    l1y_orders,
    l1y_refund_rate,

    -- 折扣敏感度
    discount_ratio,
    discount_sensitivity,

    -- 聊天指标
    chat_frequency_days,
    first_chat_date,
    last_chat_date,
    l30d_chat_frequency_days,
    l3m_chat_frequency_days,
    avg_chat_interval_days,

    -- 流失风险
    churn_risk,

    -- 地理位置
    city,

    -- 品类偏好
    top_category,
    second_category,
    third_category,

    -- 元数据
    updated_at
FROM target_buyers_precomputed
WHERE buyer_nick = %s;
