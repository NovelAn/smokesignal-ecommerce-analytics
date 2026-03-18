-- ============================================
-- 按渠道统计(DTC/PFS)
-- ============================================
-- 用途: 渠道对比分析
-- 性能: < 0.1秒(使用channel索引)
-- ============================================

SELECT
    channel,
    COUNT(*) as buyer_count,
    SUM(historical_net_sales) as total_netsales,
    AVG(historical_net_sales) as avg_netsales,
    SUM(l6m_netsales) as total_l6m_netsales,
    AVG(l6m_netsales) as avg_l6m_netsales,
    SUM(l1y_netsales) as total_l1y_netsales,
    AVG(total_orders) as avg_orders,
    AVG(refund_rate) as avg_refund_rate,

    -- VIP分布
    SUM(CASE WHEN vip_level = 'V3' THEN 1 ELSE 0 END) as v3_count,
    SUM(CASE WHEN vip_level = 'V2' THEN 1 ELSE 0 END) as v2_count,
    SUM(CASE WHEN vip_level = 'V1' THEN 1 ELSE 0 END) as v1_count,
    SUM(CASE WHEN vip_level = 'V0' THEN 1 ELSE 0 END) as v0_count,

    -- 新老客分布
    SUM(CASE WHEN client_monthly_tag = '新客户' THEN 1 ELSE 0 END) as new_customer_count,
    SUM(CASE WHEN client_monthly_tag = '老客户' THEN 1 ELSE 0 END) as old_customer_count,

    -- Smoker占比
    SUM(CASE WHEN is_smoker THEN 1 ELSE 0 END) as smoker_count,
    SUM(CASE WHEN is_vic THEN 1 ELSE 0 END) as vic_count,

    -- 流失风险
    SUM(CASE WHEN churn_risk = '高' THEN 1 ELSE 0 END) as high_churn_count,
    SUM(CASE WHEN churn_risk = '中' THEN 1 ELSE 0 END) as medium_churn_count

FROM target_buyers_precomputed
GROUP BY channel
ORDER BY total_netsales DESC;
