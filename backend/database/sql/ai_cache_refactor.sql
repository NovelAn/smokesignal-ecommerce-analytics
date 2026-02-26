-- ============================================
-- AI分析缓存表重构迁移脚本 v2.1
--
-- 目标: 一个客户一条记录，两种分析独立时间戳
--
-- 变更:
-- 1. 删除 cache_key, expires_at 等字段
-- 2. 画像和情感分析各有独立的时间戳字段
-- 3. 主键为 buyer_nick
-- ============================================

-- 备份提示
SELECT '⚠️  请确保已备份数据' AS reminder;

-- ============================================
-- Step 1: 创建新表结构
-- ============================================

DROP TABLE IF EXISTS buyer_ai_analysis_cache_new;

CREATE TABLE buyer_ai_analysis_cache_new (
    -- 主键
    buyer_nick              VARCHAR(100) PRIMARY KEY COMMENT '买家昵称',

    -- 画像分析独立时间戳
    persona_analyzed_at             TIMESTAMP NULL COMMENT '画像分析完成时间',
    persona_analyzed_last_purchase_date TIMESTAMP NULL COMMENT '画像分析时的最后订单时间',
    persona_analyzed_last_chat_date TIMESTAMP NULL COMMENT '画像分析时的最后聊天时间',

    -- 情感分析独立时间戳
    sentiment_analyzed_at           TIMESTAMP NULL COMMENT '情感分析完成时间',
    sentiment_analyzed_last_chat_date TIMESTAMP NULL COMMENT '情感分析时的最后聊天时间',

    -- AI客户画像字段 (有值=已分析)
    persona_summary             TEXT COMMENT '客户画像摘要',
    persona_key_interests       JSON COMMENT '关键兴趣点',
    persona_pain_points         JSON COMMENT '痛点',
    persona_recommended_action  TEXT COMMENT '推荐行动',
    persona_method              VARCHAR(50) COMMENT '分析方法: deepseek/zhipu/rule_based',

    -- 情感/意图分析字段 (有值=已分析)
    sentiment_score             DECIMAL(3,2) COMMENT '情绪分数(0-1)',
    sentiment_label             VARCHAR(20) COMMENT '情绪标签: Positive/Neutral/Negative',
    intent_distribution         JSON COMMENT '意图分布',
    dominant_intent             VARCHAR(50) COMMENT '主要意图',
    pre_sale_keywords           JSON COMMENT '售前关键词',
    post_sale_keywords          JSON COMMENT '售后关键词',
    complaint_count             INT DEFAULT 0 COMMENT '投诉次数',
    sentiment_method            VARCHAR(50) COMMENT '分析方法: zhipu/rule_based',

    -- 元数据
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- 索引
    INDEX idx_persona_analyzed_at (persona_analyzed_at),
    INDEX idx_sentiment_analyzed_at (sentiment_analyzed_at),
    INDEX idx_sentiment_label (sentiment_label),
    INDEX idx_dominant_intent (dominant_intent)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI分析缓存表 - v2.1';

SELECT '✅ 新表结构创建完成' AS status;

-- ============================================
-- Step 2: 迁移数据 (从旧表结构迁移)
-- ============================================

-- 注意：此迁移脚本假设旧表有以下字段:
-- buyer_nick, summary, key_interests, pain_points, recommended_action, analysis_method
-- sentiment_score, sentiment_label, intent_distribution, dominant_intent
-- pre_sale_keywords, post_sale_keywords, complaint_count, analyzed_at, created_at

INSERT INTO buyer_ai_analysis_cache_new (
    buyer_nick,
    persona_summary, persona_key_interests, persona_pain_points,
    persona_recommended_action, persona_method,
    sentiment_score, sentiment_label, intent_distribution,
    dominant_intent, pre_sale_keywords, post_sale_keywords,
    complaint_count, sentiment_method,
    created_at
)
SELECT
    buyer_nick,
    summary, key_interests, pain_points,
    recommended_action, analysis_method,
    sentiment_score, sentiment_label, intent_distribution,
    dominant_intent, pre_sale_keywords, post_sale_keywords,
    complaint_count,
    COALESCE(analysis_method, 'rule_based'),  -- 默认使用 rule_based
    created_at
FROM buyer_ai_analysis_cache;

SELECT CONCAT('📦 迁移了 ', ROW_COUNT(), ' 条记录') AS migration_result;

-- ============================================
-- Step 3: 补充数据快照
-- ============================================

-- 从 target_buyers_precomputed 补充时间戳和数据快照
UPDATE buyer_ai_analysis_cache_new cache
INNER JOIN target_buyers_precomputed tb ON cache.buyer_nick = tb.buyer_nick
SET
    -- 画像分析时间戳 (如果有画像数据)
    cache.persona_analyzed_at = CASE WHEN cache.persona_summary IS NOT NULL THEN cache.created_at ELSE NULL END,
    cache.persona_analyzed_last_purchase_date = CASE WHEN cache.persona_summary IS NOT NULL THEN tb.last_purchase_date ELSE NULL END,
    cache.persona_analyzed_last_chat_date = CASE WHEN cache.persona_summary IS NOT NULL THEN tb.last_chat_date ELSE NULL END,
    -- 情感分析时间戳 (如果有情感数据)
    cache.sentiment_analyzed_at = CASE WHEN cache.sentiment_score IS NOT NULL THEN cache.created_at ELSE NULL END,
    cache.sentiment_analyzed_last_chat_date = CASE WHEN cache.sentiment_score IS NOT NULL THEN tb.last_chat_date ELSE NULL END;

SELECT CONCAT('📊 补充了数据快照') AS snapshot_result;

-- ============================================
-- Step 4: 替换旧表
-- ============================================

RENAME TABLE
    buyer_ai_analysis_cache TO buyer_ai_analysis_cache_old,
    buyer_ai_analysis_cache_new TO buyer_ai_analysis_cache;

SELECT '✅ 表结构重构完成！' AS status;

-- ============================================
-- Step 5: 验证
-- ============================================

SELECT '📋 新表结构:' AS info;
DESCRIBE buyer_ai_analysis_cache;

SELECT '📊 数据统计:' AS info;
SELECT
    COUNT(*) as total_records,
    SUM(CASE WHEN persona_summary IS NOT NULL THEN 1 ELSE 0 END) as has_persona,
    SUM(CASE WHEN persona_analyzed_at IS NOT NULL THEN 1 ELSE 0 END) as has_persona_time,
    SUM(CASE WHEN sentiment_score IS NOT NULL THEN 1 ELSE 0 END) as has_sentiment,
    SUM(CASE WHEN sentiment_analyzed_at IS NOT NULL THEN 1 ELSE 0 END) as has_sentiment_time
FROM buyer_ai_analysis_cache;

-- ============================================
-- (可选) Step 6: 删除旧表
-- ============================================

-- 确认无误后执行:
-- DROP TABLE IF EXISTS buyer_ai_analysis_cache_old;
