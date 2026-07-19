-- ============================================
-- 分群计数: 匹配买家数量 (实时预览用)
-- ============================================
-- 与 get_segment_buyers.sql 共享完全相同的 WHERE 条件
-- ============================================

SELECT COUNT(*) AS total
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
    [[AND DATEDIFF(NOW(), last_purchase_date) <= %(max_days_since_purchase)s]];
