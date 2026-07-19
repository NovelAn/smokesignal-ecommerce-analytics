-- ============================================
-- 分群查询: 按标签组合筛选买家 (核心 P0 功能)
-- ============================================
-- 用途: 用户分群构建器 — 灵活组合标签和指标范围圈选人群
-- 性能: < 0.5秒 (预计算表 + 索引)
-- 模式: [[CONDITION]] 由 Python 动态移除未使用的条件
-- ============================================

SELECT
    buyer_nick,
    channel,
    buyer_type,
    is_smoker,
    is_vic,
    vip_level,
    lifecycle_stage,
    client_monthly_tag,
    rfm_segment,
    churn_risk,
    discount_sensitivity,
    sentiment_label,
    dominant_intent,
    follow_priority,
    top_category,
    second_category,
    third_category,
    city,
    historical_gmv,
    historical_net_sales,
    rolling_24m_netsales,
    l6m_netsales,
    l1y_netsales,
    total_orders,
    total_net_orders,
    refund_rate,
    avg_purchase_interval_days,
    last_purchase_date,
    last_chat_date,
    chat_frequency_days,
    l3m_chat_frequency_days
FROM target_buyers_precomputed
WHERE 1=1
    [[AND buyer_type IN %(buyer_type)s]]
    [[AND vip_level IN %(vip_level)s]]
    [[AND lifecycle_stage IN %(lifecycle_stage)s]]
    [[AND churn_risk IN %(churn_risk)s]]
    [[AND channel IN %(channel)s]]
    [[AND sentiment_label IN %(sentiment_label)s]]
    [[AND dominant_intent IN %(dominant_intent)s]]
    [[AND follow_priority IN %(follow_priority)s]]
    [[AND client_monthly_tag IN %(client_monthly_tag)s]]
    [[AND top_category IN %(top_category)s]]
    [[AND discount_sensitivity IN %(discount_sensitivity)s]]
    [[AND historical_gmv >= %(min_gmv)s]]
    [[AND historical_gmv <= %(max_gmv)s]]
    [[AND total_orders >= %(min_orders)s]]
    [[AND total_orders <= %(max_orders)s]]
    [[AND refund_rate >= %(min_refund_rate)s]]
    [[AND refund_rate <= %(max_refund_rate)s]]
    [[AND l6m_netsales >= %(min_l6m_netsales)s]]
    [[AND l6m_netsales <= %(max_l6m_netsales)s]]
    [[AND avg_purchase_interval_days >= %(min_purchase_interval)s]]
    [[AND avg_purchase_interval_days <= %(max_purchase_interval)s]]
    [[AND DATEDIFF(NOW(), last_purchase_date) >= %(min_days_since_purchase)s]]
    [[AND DATEDIFF(NOW(), last_purchase_date) <= %(max_days_since_purchase)s]]
ORDER BY rolling_24m_netsales DESC
LIMIT %(limit)s OFFSET %(offset)s;
