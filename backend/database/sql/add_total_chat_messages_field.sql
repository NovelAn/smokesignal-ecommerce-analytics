-- Migration: 添加 total_chat_messages 字段
-- 统计客户发送的消息条数 (sender_nick = user_nick)，排除客服自动回复
-- Date: 2026-02-27

-- 1. 添加字段（如果不存在）
ALTER TABLE target_buyers_precomputed
ADD COLUMN IF NOT EXISTS total_chat_messages INT COMMENT '客户发送的消息总条数(sender_nick=user_nick)' AFTER chat_frequency_days;

-- 2. 初始化数据 - 只统计客户发送的消息
UPDATE target_buyers_precomputed tb
SET total_chat_messages = (
    SELECT COUNT(*)
    FROM chat_history
    WHERE user_nick = tb.buyer_nick
      AND sender_nick = tb.buyer_nick
)
WHERE total_chat_messages IS NULL;

-- 3. 验证
SELECT
    COUNT(*) as total_buyers,
    SUM(CASE WHEN total_chat_messages >= 5 THEN 1 ELSE 0 END) as buyers_with_5plus_messages,
    SUM(CASE WHEN total_chat_messages >= 5 AND sentiment_label IS NOT NULL THEN 1 ELSE 0 END) as analyzed_buyers
FROM target_buyers_precomputed;

-- 查看示例数据
SELECT buyer_nick, total_chat_messages, chat_frequency_days, sentiment_label
FROM target_buyers_precomputed
WHERE total_chat_messages >= 5
ORDER BY total_chat_messages DESC
LIMIT 20;
