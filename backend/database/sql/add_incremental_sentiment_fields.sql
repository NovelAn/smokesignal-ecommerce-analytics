-- ============================================
-- 增量情感分析字段 (CRM Round 1 升级)
-- 用途: 区分"标记后新增聊天产生的负面"vs"持续老负面"
-- 兼容: 现有数据 incremental_* 字段全部 NULL，新分析会自然填充
-- 更新: 2026-06-11
-- ============================================

-- Step 1: 添加增量分析相关字段
ALTER TABLE buyer_ai_analysis_cache
    ADD COLUMN incremental_chat_count INT DEFAULT 0
        COMMENT '增量分析覆盖的聊天数',
    ADD COLUMN incremental_chat_from_date TIMESTAMP NULL
        COMMENT '增量分析起点(=上次 sentiment_analyzed_last_chat_date)',
    ADD COLUMN incremental_chat_to_date TIMESTAMP NULL
        COMMENT '增量分析终点(=本次分析覆盖到的最早一条聊天时间)',
    ADD COLUMN incremental_sentiment_label VARCHAR(20) NULL
        COMMENT '增量情感: Positive/Neutral/Negative',
    ADD COLUMN incremental_sentiment_score DECIMAL(3,2) NULL
        COMMENT '增量情感分数(0-1)',
    ADD COLUMN incremental_sentiment_analyzed_at TIMESTAMP NULL
        COMMENT '增量分析时间';

-- Step 2: 添加索引（提高重激活 EXISTS 子查询性能）
ALTER TABLE buyer_ai_analysis_cache
    ADD INDEX idx_incremental_label (incremental_sentiment_label),
    ADD INDEX idx_incremental_analyzed_at (incremental_sentiment_analyzed_at);
