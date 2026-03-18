-- ============================================
-- RFM 客户分类简化迁移脚本
-- ============================================
-- 简化版： 11种分类，-- 覆盖所有 125 种组合
-- 符合奢品男装行业特性
-- ============================================
-- 执行方式:
-- 方式1: 直接执行整个文件
-- mysql -u username -p database_name < migrate_rfm_simple.sql
--
-- 方式2: 分步执行
-- 复制下面的 SQL 语句到 MySQL 客户端执行
-- ============================================

-- ============================================
-- Phase 1: 计算 RFM 分数
-- ============================================

-- R 分数 (最近购买时间)
UPDATE target_buyers_precomputed
SET rfm_recency_score = CASE
    WHEN last_purchase_date IS NULL THEN 0
    WHEN DATEDIFF(NOW(), last_purchase_date) <= 60 THEN 5
    WHEN DATEDIFF(NOW(), last_purchase_date) <= 180 THEN 4
    WHEN DATEDIFF(NOW(), last_purchase_date) <= 365 THEN 3
    WHEN DATEDIFF(NOW(), last_purchase_date) <= 730 THEN 2
    ELSE 1
END;

-- F 分数(购买频次)
UPDATE target_buyers_precomputed
SET rfm_frequency_score = CASE
    WHEN total_orders >= 5 THEN 5
    WHEN total_orders >= 3 THEN 4
    WHEN total_orders = 2 THEN 3
    WHEN total_orders = 1 AND chat_frequency_days > 0 THEN 2
    WHEN total_orders = 1 THEN 1
    ELSE 0
END;

-- M 分数(消费金额)
UPDATE target_buyers_precomputed
SET rfm_monetary_score = CASE
    WHEN historical_net_sales >= 50000 THEN 5
    WHEN historical_net_sales >= 20000 THEN 4
    WHEN historical_net_sales >= 10000 THEN 3
    WHEN historical_net_sales >= 5000 THEN 2
    ELSE 1
END;

-- ============================================
-- Phase 2: 确定 RFM 客户分类 (简化版 - 11种)
-- ============================================

UPDATE target_buyers_precomputed
SET rfm_segment = CASE
    -- ============================================
    -- M=5 (≥50K) - 核心VIP客户群
    -- ============================================
    WHEN rfm_monetary_score = 5 AND rfm_recency_score >= 4 AND rfm_frequency_score >= 4
        THEN '重要价值客户'
    WHEN rfm_monetary_score = 5 AND rfm_recency_score >= 4 AND rfm_frequency_score <= 3
        THEN '重要发展客户'
    WHEN rfm_monetary_score = 5 AND rfm_recency_score <= 3 AND rfm_frequency_score >= 4
        THEN '重要保持客户'
    WHEN rfm_monetary_score = 5 AND rfm_recency_score <= 3 AND rfm_frequency_score <= 3
        THEN '重要挽留客户'

    -- ============================================
    -- M=4 (20K-50K) - 高价值客户群
    -- ============================================
    WHEN rfm_monetary_score = 4 AND rfm_recency_score >= 4 AND rfm_frequency_score >= 4
        THEN '优质活跃客户'
    WHEN rfm_monetary_score = 4 AND rfm_recency_score >= 4 AND rfm_frequency_score = 3
        THEN '优质发展客户'
    WHEN rfm_monetary_score = 4 AND rfm_recency_score >= 4 AND rfm_frequency_score <= 2
        THEN '优质新客'
    WHEN rfm_monetary_score = 4 AND rfm_recency_score <= 3 AND rfm_frequency_score >= 3
        THEN '优质保持客户'
    WHEN rfm_monetary_score = 4 AND rfm_recency_score <= 3 AND rfm_frequency_score <= 2
        THEN '优质挽留客户'

    -- ============================================
    -- M=3 (10K-20K) - 中等价值客户群
    -- ============================================
    WHEN rfm_monetary_score = 3 AND rfm_recency_score >= 4 AND rfm_frequency_score >= 4
        THEN '成长活跃客户'
    WHEN rfm_monetary_score = 3 AND rfm_recency_score >= 4 AND rfm_frequency_score = 3
        THEN '成长发展客户'
    WHEN rfm_monetary_score = 3 AND rfm_recency_score >= 4 AND rfm_frequency_score <= 2
        THEN '成长新客'
    WHEN rfm_monetary_score = 3 AND rfm_recency_score <= 3 AND rfm_frequency_score >= 3
        THEN '成长保持客户'
    WHEN rfm_monetary_score = 3 AND rfm_recency_score <= 3 AND rfm_frequency_score <= 2
        THEN '成长挽留客户'

    -- ============================================
    -- M=2 (5K-10K) - 潜力客户群
    -- ============================================
    WHEN rfm_monetary_score = 2 AND rfm_recency_score >= 4
        THEN '潜力客户'
    WHEN rfm_monetary_score = 2 AND rfm_recency_score <= 3
        THEN '待激活客户'

    -- ============================================
    -- M=1 (<5K) - 入门客户群
    -- ============================================
    WHEN rfm_monetary_score = 1 AND rfm_recency_score >= 4
        THEN '新客户'
    WHEN rfm_monetary_score = 1 AND rfm_recency_score IN (2, 3)
        THEN '低价值客户'

    -- ============================================
    -- 特殊情况
    -- ============================================
    WHEN rfm_recency_score = 1
        THEN '已流失'
    WHEN rfm_recency_score = 0
        THEN '无购买记录'

    ELSE '待分类'
END;

-- ============================================
-- Phase 3: 计算跟进优先级
-- ============================================

UPDATE target_buyers_precomputed
SET follow_priority = CASE
    -- 紧急
    WHEN rfm_segment IN ('重要价值客户', '重要保持客户', '重要挽留客户') THEN '紧急'
    -- 高
    WHEN rfm_segment IN ('重要发展客户', '优质活跃客户', '优质发展客户', '优质新客', '优质保持客户', '优质挽留客户') THEN '高'
    -- 中
    WHEN rfm_segment IN ('成长活跃客户', '成长发展客户', '成长新客', '成长保持客户', '成长挽留客户', '潜力客户', '新客户') THEN '中'
    -- 低
    WHEN rfm_segment IN ('待激活客户', '低价值客户', '已流失', '无购买记录') THEN '低'
    ELSE '中'
END;

-- ============================================
-- Phase 4: 风险升级
-- ============================================

-- 高流失风险升级优先级
UPDATE target_buyers_precomputed
SET follow_priority = '高'
WHERE churn_risk = '高' AND follow_priority IN ('中', '低');

    AND follow_priority != '紧急';

-- VIP客户升级优先级
UPDATE target_buyers_precomputed
SET follow_priority = '高'
WHERE vip_level IN ('V3', 'V2') AND follow_priority = '中';

-- ============================================
-- Phase 5: 风险升级
-- ============================================

-- 高流失风险升级优先级
UPDATE target_buyers_precomputed
SET follow_priority = '高'
WHERE churn_risk = '高' AND follow_priority IN ('中', '低');

    AND follow_priority != '紧急';

-- VIP客户升级优先级
UPDATE target_buyers_precomputed
SET follow_priority = '高'
WHERE vip_level IN ('V3', 'V2') AND follow_priority = '中';

-- ============================================
-- Phase 6: 鰭证结果
-- ============================================

SELECT '✅ RFM 分类迁移完成' AS message;

SELECT '==========================================-' AS separator;
SELECT '📊 RFM 分数分布:' AS report_type;

SELECT
    rfm_recency_score as r分数,
    COUNT(*) as 客户数
FROM target_buyers_precomputed
GROUP BY rfm_recency_score
ORDER BY rfm_recency_score;

    ;

SELECT '==========================================-' AS separator;
SELECT '📊 客户分类分布:' AS report_type;
SELECT
    rfm_segment as 客户分类,
    COUNT(*) as 客户数,
    ROUND(AVG(historical_net_sales), 0) as 平均消费
FROM target_buyers_precomputed
WHERE rfm_segment IS NOT NULL
GROUP BY rfm_segment
ORDER BY 客户数 DESC
    ;

SELECT '==========================================-' AS separator;
SELECT '📊 跟进优先级分布:' AS report_type;
SELECT
    follow_priority as 优先级,
    COUNT(*) as 客户数
FROM target_buyers_precomputed
WHERE follow_priority IS NOT NULL
GROUP BY follow_priority
ORDER BY FIELD(follow_priority, '紧急', '高', '中', '低')
    ;

SELECT '==========================================-' AS separator;
SELECT '🔍 检查待分类客户:' AS check;
SELECT COUNT(*) as unclassified_count
FROM target_buyers_precomputed
WHERE rfm_segment = '待分类';
    ;
SELECT CONCAT('   - 待分类: ', IFNULL(unclassified_count, 0), unclassified_count, ELSE '0') ELSE '无') AS result
    ;
SELECT '🎉 迁移完成!' AS message;
