-- ============================================
-- RFM模型 + 情绪/意图分析字段迁移脚本
-- ============================================
-- 功能：
-- 1. 添加RFM分数和客户分类字段
-- 2. 添加情绪和意图分析字段
-- 3. 添加运营标签字段
-- ============================================

-- ============================================
-- Phase 1: RFM客户分类模型字段
-- ============================================

ALTER TABLE target_buyers_precomputed
ADD COLUMN rfm_recency_score INT DEFAULT 0 COMMENT 'R分数(1-5): 最近购买时间',
ADD COLUMN rfm_frequency_score INT DEFAULT 0 COMMENT 'F分数(1-5): 购买频次',
ADD COLUMN rfm_monetary_score INT DEFAULT 0 COMMENT 'M分数(1-5): 消费金额',
ADD COLUMN rfm_segment VARCHAR(50) COMMENT 'RFM客户分类: 重要价值/重要发展/重要保持/一般价值/潜力/流失预警/已流失',
ADD INDEX idx_rfm_segment (rfm_segment);

-- ============================================
-- Phase 3: 情绪与意图分析字段
-- ============================================

ALTER TABLE target_buyers_precomputed
ADD COLUMN sentiment_label VARCHAR(20) COMMENT '整体情绪标签: Positive/Neutral/Negative',
ADD COLUMN sentiment_score DECIMAL(3,2) COMMENT '情绪分数(0-1)',
ADD COLUMN dominant_intent VARCHAR(50) COMMENT '主要意图: Pre-sale Inquiry/Post-sale Support/Logistics/Usage Guide/Complaint',
ADD COLUMN pre_sale_score INT DEFAULT 0 COMMENT '售前热度(0-100)',
ADD COLUMN post_sale_score INT DEFAULT 0 COMMENT '售后需求(0-100)',
ADD COLUMN complaint_tendency VARCHAR(10) COMMENT '投诉倾向: 高/中/低',
ADD COLUMN follow_priority VARCHAR(10) COMMENT '跟进优先级: 紧急/高/中/低',
ADD INDEX idx_sentiment (sentiment_label),
ADD INDEX idx_intent (dominant_intent),
ADD INDEX idx_follow_priority (follow_priority);

-- ============================================
-- 扩展AI分析缓存表
-- ============================================

-- 检查表是否存在，如果不存在则创建
CREATE TABLE IF NOT EXISTS buyer_ai_analysis_cache (
    buyer_nick VARCHAR(255) PRIMARY KEY COMMENT '买家昵称',
    sentiment_score DECIMAL(3,2) COMMENT '情绪分数(0-1)',
    sentiment_label VARCHAR(20) COMMENT '情绪标签(Positive/Neutral/Negative)',
    intent_distribution JSON COMMENT '意图分布',
    dominant_intent VARCHAR(50) COMMENT '主要意图',
    pre_sale_keywords JSON COMMENT '售前关键词',
    post_sale_keywords JSON COMMENT '售后关键词',
    complaint_count INT DEFAULT 0 COMMENT '投诉次数',
    analyzed_at TIMESTAMP COMMENT '分析时间',
    analysis_version VARCHAR(20) COMMENT '分析版本',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_analyzed_at (analyzed_at),
    INDEX idx_sentiment (sentiment_label),
    INDEX idx_intent (dominant_intent)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='买家AI分析缓存表';

-- ============================================
-- RFM分数计算存储过程
-- ============================================

DROP PROCEDURE IF EXISTS calculate_rfm_scores;

DELIMITER $$

CREATE PROCEDURE calculate_rfm_scores()
BEGIN
    DECLARE start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

    SELECT '🚀 开始计算RFM分数...' AS message;

    -- 计算R分数 (Recency - 最近购买时间)
    -- 奢侈品场景优化阈值：60天/180天/365天/730天
    UPDATE target_buyers_precomputed
    SET rfm_recency_score = CASE
        WHEN last_purchase_date IS NULL THEN 0
        WHEN DATEDIFF(NOW(), last_purchase_date) <= 60 THEN 5      -- 2个月内
        WHEN DATEDIFF(NOW(), last_purchase_date) <= 180 THEN 4     -- 6个月内
        WHEN DATEDIFF(NOW(), last_purchase_date) <= 365 THEN 3     -- 1年内
        WHEN DATEDIFF(NOW(), last_purchase_date) <= 730 THEN 2     -- 2年内
        ELSE 1                                                      -- 超过2年
    END;

    -- 计算F分数 (Frequency - 购买频次)
    -- 奢侈品场景优化阈值：5单/3-4单/2单/1单+聊天
    UPDATE target_buyers_precomputed
    SET rfm_frequency_score = CASE
        WHEN total_orders >= 5 THEN 5                               -- 5单以上
        WHEN total_orders >= 3 THEN 4                               -- 3-4单
        WHEN total_orders = 2 THEN 3                                -- 2单
        WHEN total_orders = 1 AND chat_frequency_days > 0 THEN 2    -- 1单+有聊天
        WHEN total_orders = 1 THEN 1                                -- 1单+无聊天
        ELSE 0
    END;

    -- 计算M分数 (Monetary - 消费金额)
    -- 奢侈品场景优化阈值：50K/20K/10K/5K
    UPDATE target_buyers_precomputed
    SET rfm_monetary_score = CASE
        WHEN historical_net_sales >= 50000 THEN 5                   -- 5万以上
        WHEN historical_net_sales >= 20000 THEN 4                   -- 2-5万
        WHEN historical_net_sales >= 10000 THEN 3                   -- 1-2万
        WHEN historical_net_sales >= 5000 THEN 2                    -- 5千-1万
        ELSE 1                                                      -- 5千以下
    END;

    -- 计算客户分类 (基于RFM分数组合)
    UPDATE target_buyers_precomputed
    SET rfm_segment = CASE
        -- 重要价值客户: R≥4, F≥4, M≥4 (高频高消费且最近活跃)
        WHEN rfm_recency_score >= 4 AND rfm_frequency_score >= 4 AND rfm_monetary_score >= 4
            THEN '重要价值客户'

        -- 重要发展客户: R≥4, F≤2, M≥4 (高消费但频次低)
        WHEN rfm_recency_score >= 4 AND rfm_frequency_score <= 2 AND rfm_monetary_score >= 4
            THEN '重要发展客户'

        -- 重要保持客户: R≤2, F≥4, M≥4 (曾经高频高消费但近期沉默)
        WHEN rfm_recency_score <= 2 AND rfm_frequency_score >= 4 AND rfm_monetary_score >= 4
            THEN '重要保持客户'

        -- 一般价值客户: R≥3, F≥3, M≥3 (中等活跃度)
        WHEN rfm_recency_score >= 3 AND rfm_frequency_score >= 3 AND rfm_monetary_score >= 3
            THEN '一般价值客户'

        -- 潜力客户: R≥4, F≤2, M≤2 (新客户，有潜力)
        WHEN rfm_recency_score >= 4 AND rfm_frequency_score <= 2 AND rfm_monetary_score <= 2
            THEN '潜力客户'

        -- 流失预警: R≤2, F≤2, M≥3 (曾经有价值但可能流失)
        WHEN rfm_recency_score <= 2 AND rfm_frequency_score <= 2 AND rfm_monetary_score >= 3
            THEN '流失预警'

        -- 已流失: R=1, F任意, M任意 (长期无活动)
        WHEN rfm_recency_score = 1
            THEN '已流失'

        ELSE '待分类'
    END;

    -- 输出统计信息
    SELECT '✅ RFM分数计算完成！' AS message;
    SELECT CONCAT('⏱️  总耗时: ', TIMESTAMPDIFF(SECOND, start_time, CURRENT_TIMESTAMP), ' 秒') AS duration;

    -- 按客户分类统计
    SELECT
        rfm_segment,
        COUNT(*) as count,
        ROUND(AVG(historical_net_sales), 2) as avg_netsales,
        ROUND(AVG(total_orders), 2) as avg_orders
    FROM target_buyers_precomputed
    WHERE rfm_segment IS NOT NULL
    GROUP BY rfm_segment
    ORDER BY count DESC;

END$$

DELIMITER ;

-- ============================================
-- 执行RFM计算
-- ============================================

-- 取消注释以下行来立即执行RFM计算
-- CALL calculate_rfm_scores();

-- ============================================
-- 验证查询
-- ============================================

-- 查看RFM分布
-- SELECT
--     rfm_segment,
--     COUNT(*) as count,
--     ROUND(AVG(rfm_recency_score), 2) as avg_r,
--     ROUND(AVG(rfm_frequency_score), 2) as avg_f,
--     ROUND(AVG(rfm_monetary_score), 2) as avg_m
-- FROM target_buyers_precomputed
-- GROUP BY rfm_segment
-- ORDER BY count DESC;

-- 查看重要价值客户
-- SELECT buyer_nick, vip_level, rfm_segment, historical_net_sales, total_orders, last_purchase_date
-- FROM target_buyers_precomputed
-- WHERE rfm_segment = '重要价值客户'
-- ORDER BY historical_net_sales DESC
-- LIMIT 20;

-- 查看流失预警客户
-- SELECT buyer_nick, vip_level, rfm_segment, historical_net_sales, total_orders, last_purchase_date
-- FROM target_buyers_precomputed
-- WHERE rfm_segment = '流失预警'
-- ORDER BY historical_net_sales DESC
-- LIMIT 20;
