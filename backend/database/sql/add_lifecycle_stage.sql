-- ============================================
-- 迁移: 添加 lifecycle_stage 生命周期阶段字段
-- ============================================
-- 日期: 2026-06-13
-- 用途: 用户分群功能 — 生命周期分层
-- 阶段: 流失 → 新客 → 成熟 → 成长 → 预流失 (优先级从高到低)
-- ============================================

-- 1. 添加列 (在 churn_risk 之后)
ALTER TABLE target_buyers_precomputed
  ADD COLUMN lifecycle_stage VARCHAR(20) COMMENT '生命周期阶段: 新客/成长/成熟/预流失/流失'
  AFTER churn_risk;

-- 2. 添加索引
CREATE INDEX idx_lifecycle_stage ON target_buyers_precomputed(lifecycle_stage);

-- 3. 回填现有数据
UPDATE target_buyers_precomputed
SET lifecycle_stage = CASE
    -- 流失: 最后购买超过1年 OR 高流失风险
    WHEN DATEDIFF(NOW(), last_purchase_date) > 365 OR churn_risk = '高'
      THEN '流失'
    -- 新客: 首次购买在90天内
    WHEN DATEDIFF(NOW(), first_purchase_date) <= 90
      THEN '新客'
    -- 成熟: 高净值(rolling_24m >= 50K) 且 近期活跃(180天内有购买)
    WHEN rolling_24m_netsales >= 50000
         AND DATEDIFF(NOW(), last_purchase_date) <= 180
      THEN '成熟'
    -- 成长: 首次购买91-365天 且 近期有购买(90天内) 且 净值 < 50K
    WHEN DATEDIFF(NOW(), first_purchase_date) BETWEEN 91 AND 365
         AND DATEDIFF(NOW(), last_purchase_date) <= 90
         AND rolling_24m_netsales < 50000
      THEN '成长'
    -- 预流失: 兜底 (不满足以上任何条件的活跃客户)
    ELSE '预流失'
END;

-- 4. 验证分布
SELECT lifecycle_stage, COUNT(*) as count,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM target_buyers_precomputed), 1) as pct
FROM target_buyers_precomputed
GROUP BY lifecycle_stage
ORDER BY FIELD(lifecycle_stage, '新客', '成长', '成熟', '预流失', '流失');
