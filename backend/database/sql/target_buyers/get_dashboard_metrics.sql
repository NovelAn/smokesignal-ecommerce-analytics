-- ============================================
-- 获取Dashboard汇总指标 (v2.0 - 运营导向)
-- ============================================
-- 用途: Dashboard概览页顶部卡片
-- 性能: < 0.1秒(直接聚合预计算表)
-- 分组:
--   1. 客户健康度（情感分布）
--   2. 跟进优先级分布
--   3. 销售机会（复购潜力/VIC/SMOKER）
--   4. 服务质量（流失风险）
-- ============================================

SELECT
    -- 基础统计
    COUNT(*) as total_target_buyers,
    SUM(CASE WHEN is_smoker THEN 1 ELSE 0 END) as total_smokers,
    SUM(CASE WHEN is_vic THEN 1 ELSE 0 END) as total_vics,
    SUM(CASE WHEN buyer_type = 'BOTH' THEN 1 ELSE 0 END) as both_smoker_vic,

    -- 情感分布（客户健康度）
    SUM(CASE WHEN sentiment_label = 'Positive' THEN 1 ELSE 0 END) as positive_sentiment_count,
    SUM(CASE WHEN sentiment_label = 'Neutral' THEN 1 ELSE 0 END) as neutral_sentiment_count,
    SUM(CASE WHEN sentiment_label = 'Negative' THEN 1 ELSE 0 END) as negative_sentiment_count,

    -- 跟进优先级分布
    SUM(CASE WHEN follow_priority = '紧急' THEN 1 ELSE 0 END) as urgent_priority_count,
    SUM(CASE WHEN follow_priority = '高' THEN 1 ELSE 0 END) as high_priority_count,
    SUM(CASE WHEN follow_priority = '中' THEN 1 ELSE 0 END) as medium_priority_count,
    SUM(CASE WHEN follow_priority = '低' THEN 1 ELSE 0 END) as low_priority_count,

    -- 销售机会（近6月有购买 = 复购潜力）
    SUM(CASE WHEN l6m_netsales > 0 THEN 1 ELSE 0 END) as repurchase_potential_count,

    -- 流失风险分布
    SUM(CASE WHEN churn_risk = '高' THEN 1 ELSE 0 END) as high_churn_count,
    SUM(CASE WHEN churn_risk = '中' THEN 1 ELSE 0 END) as medium_churn_count,
    SUM(CASE WHEN churn_risk = '低' THEN 1 ELSE 0 END) as low_churn_count,

    -- 最后更新时间
    MAX(updated_at) as last_updated
FROM target_buyers_precomputed;
