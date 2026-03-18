-- ============================================
-- 获取Dashboard汇总指标
-- ============================================
-- 用途: Dashboard概览页顶部卡片
-- 性能: < 0.1秒(直接聚合预计算表)
-- ============================================

SELECT
    -- 买家数量
    COUNT(*) as total_target_buyers,
    SUM(CASE WHEN is_smoker THEN 1 ELSE 0 END) as total_smokers,
    SUM(CASE WHEN is_vic THEN 1 ELSE 0 END) as total_vics,
    SUM(CASE WHEN buyer_type = 'BOTH' THEN 1 ELSE 0 END) as both_smoker_vic,

    -- 金额指标
    SUM(historical_net_sales) as total_netsales,
    AVG(historical_net_sales) as avg_netsales,
    SUM(l6m_netsales) as total_l6m_netsales,
    SUM(l1y_netsales) as total_l1y_netsales,

    -- 订单指标
    SUM(total_orders) as total_orders,
    AVG(total_orders) as avg_orders_per_buyer,

    -- 退款指标
    AVG(refund_rate) as avg_refund_rate,

    -- VIP分布
    SUM(CASE WHEN vip_level = 'V3' THEN 1 ELSE 0 END) as v3_count,
    SUM(CASE WHEN vip_level = 'V2' THEN 1 ELSE 0 END) as v2_count,
    SUM(CASE WHEN vip_level = 'V1' THEN 1 ELSE 0 END) as v1_count,
    SUM(CASE WHEN vip_level = 'V0' THEN 1 ELSE 0 END) as v0_count,
    SUM(CASE WHEN vip_level = 'Non-VIP' THEN 1 ELSE 0 END) as non_vip_count,

    -- 渠道分布
    SUM(CASE WHEN channel = 'DTC' THEN 1 ELSE 0 END) as dtc_count,
    SUM(CASE WHEN channel = 'PFS' THEN 1 ELSE 0 END) as pfs_count,

    -- 流失风险分布
    SUM(CASE WHEN churn_risk = '高' THEN 1 ELSE 0 END) as high_churn_count,
    SUM(CASE WHEN churn_risk = '中' THEN 1 ELSE 0 END) as medium_churn_count,
    SUM(CASE WHEN churn_risk = '低' THEN 1 ELSE 0 END) as low_churn_count,

    -- 折扣敏感度分布
    SUM(CASE WHEN discount_sensitivity = '高度敏感' THEN 1 ELSE 0 END) as high_discount_count,
    SUM(CASE WHEN discount_sensitivity = '中度敏感' THEN 1 ELSE 0 END) as medium_discount_count,
    SUM(CASE WHEN discount_sensitivity = '低度敏感' THEN 1 ELSE 0 END) as low_discount_count,

    -- 最后更新时间
    MAX(updated_at) as last_updated
FROM target_buyers_precomputed;
