-- ============================================
-- 添加新的聊天指标到预计算表
-- ============================================
-- 功能：为target_buyers_precomputed表添加新的聊天指标字段
-- 执行方式：mysql -u username -p database_name < add_chat_metrics_to_precomputed.sql
-- ============================================

-- 添加新字段
ALTER TABLE target_buyers_precomputed
ADD COLUMN first_chat_date DATETIME COMMENT '首次聊天时间' AFTER last_chat_date,
ADD COLUMN l30d_chat_frequency_days INT COMMENT '近30天沟通频次(去重日期天数)' AFTER first_chat_date,
ADD COLUMN avg_chat_interval_days DECIMAL(10, 2) COMMENT '平均沟通间隔天数' AFTER l3m_chat_frequency_days;

-- 更新现有数据
UPDATE target_buyers_precomputed tb
SET
    first_chat_date = (
        SELECT MIN(msg_time)
        FROM chat_history
        WHERE user_nick = tb.buyer_nick
    ),
    l30d_chat_frequency_days = (
        SELECT COUNT(DISTINCT DATE(msg_time))
        FROM chat_history
        WHERE user_nick = tb.buyer_nick
          AND msg_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    ),
    avg_chat_interval_days = (
        SELECT
            CASE
                WHEN COUNT(DISTINCT DATE(msg_time)) <= 1 THEN 0
                ELSE DATEDIFF(
                    MAX(DATE(msg_time)),
                    MIN(DATE(msg_time))
                ) / (COUNT(DISTINCT DATE(msg_time)) - 1)
            END
        FROM chat_history
        WHERE user_nick = tb.buyer_nick
    );

-- 验证更新结果
SELECT
    buyer_nick,
    chat_frequency_days,
    first_chat_date,
    last_chat_date,
    l30d_chat_frequency_days,
    l3m_chat_frequency_days,
    avg_chat_interval_days
FROM target_buyers_precomputed
LIMIT 10;
