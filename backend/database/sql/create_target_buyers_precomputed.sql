-- ============================================
-- 目标买家预计算表创建和更新脚本
-- ============================================
-- 功能：
-- 1. 识别Smoker买家(购买过Pipes或Lighters品类)
-- 2. 识别VIC买家(Rolling 24个月净销售 >= 30K)
-- 3. 预计算所有关键指标
-- 4. 每天上午11点自动更新
-- ============================================

-- ============================================
-- 步骤1: 创建目标买家预计算表
-- ============================================

DROP TABLE IF EXISTS target_buyers_precomputed;

CREATE TABLE target_buyers_precomputed (
    -- === 主键和基本信息 ===
    buyer_nick VARCHAR(255) PRIMARY KEY COMMENT '买家昵称',
    channel VARCHAR(10) COMMENT '渠道: DTC/PFS',
    client_monthly_tag VARCHAR(50) COMMENT '新老客标识: 新客户/老客户',

    -- === 买家类型标签 ===
    buyer_type VARCHAR(50) COMMENT '买家类型: SMOKER/VIC/BOTH',
    is_smoker BOOLEAN DEFAULT FALSE COMMENT '是否为Smoker买家',
    is_vic BOOLEAN DEFAULT FALSE COMMENT '是否为VIC买家',
    vip_level VARCHAR(10) COMMENT 'VIP等级: V3/V2/V1/V0/Non-VIP',

    -- === 历史指标(全部时间) ===
    historical_gmv DECIMAL(18, 2) COMMENT '历史GMV(成交总金额)',
    historical_refund DECIMAL(18, 2) COMMENT '历史退款总额',
    historical_net_sales DECIMAL(18, 2) COMMENT '历史净销售 = GMV - 退款',
    total_orders INT COMMENT '历史总订单数',
    total_net_orders INT COMMENT '历史有效订单数(去除退款)',
    refund_rate DECIMAL(5, 4) COMMENT '退款率 = 退款金额 / GMV (0-1)',
    first_purchase_date DATETIME COMMENT '首次购买时间',
    last_purchase_date DATETIME COMMENT '最后购买时间',

    -- === Rolling 24个月指标(用于VIP计算) ===
    rolling_24m_gmv DECIMAL(18, 2) COMMENT 'Rolling 24个月GMV(包含退款)',
    rolling_24m_netsales DECIMAL(18, 2) COMMENT 'Rolling 24个月净销售',
    rolling_24m_orders INT COMMENT 'Rolling 24个月订单数(包含退款)',
    rolling_24m_net_orders INT COMMENT 'Rolling 24个月净订单数(去除退款)',

    -- === L6M指标(近6个月) ===
    l6m_netsales DECIMAL(18, 2) COMMENT '近6个月净销售金额',
    l6m_gmv DECIMAL(18, 2) COMMENT '近6个月GMV(包含退款)',
    l6m_orders INT COMMENT '近6个月订单数',
    l6m_refund_rate DECIMAL(5, 4) COMMENT '近6个月退款率',

    -- === L1Y指标(近1年) ===
    l1y_netsales DECIMAL(18, 2) COMMENT '近1年净销售金额',
    l1y_gmv DECIMAL(18, 2) COMMENT '近1年GMV(包含退款)',
    l1y_orders INT COMMENT '近1年订单数',
    l1y_refund_rate DECIMAL(5, 4) COMMENT '近1年退款率',

    -- === 购买频率 ===
    avg_purchase_interval_days DECIMAL(10, 2) COMMENT '平均购买间隔天数(越小越频繁)',

    -- === 折扣敏感度 ===
    discount_ratio DECIMAL(5, 2) COMMENT '折扣品订单占比(0-1)',
    discount_sensitivity VARCHAR(20) COMMENT '折扣敏感度: 高度/中度/低度',

    -- === 聊天指标 ===
    chat_frequency_days INT COMMENT '历史沟通频次(去重日期天数)',
    total_chat_messages INT COMMENT '客户发送的消息总条数(sender_nick=user_nick)',
    last_chat_date DATETIME COMMENT '最后聊天时间',
    first_chat_date DATETIME COMMENT '首次聊天时间',
    l30d_chat_frequency_days INT COMMENT '近30天沟通频次(去重日期天数)',
    l3m_chat_frequency_days INT COMMENT '近3个月沟通频次(去重日期天数)',
    avg_chat_interval_days DECIMAL(10, 2) COMMENT '平均沟通间隔天数',

    -- === 流失风险标签 ===
    churn_risk VARCHAR(20) COMMENT '流失风险: 高/中/低',

    -- === 地理位置 ===
    city VARCHAR(100) COMMENT '城市',

    -- === 品类偏好(前三位) ===
    top_category VARCHAR(50) COMMENT '最常购买品类',
    second_category VARCHAR(50) COMMENT '第二常购品类',
    third_category VARCHAR(50) COMMENT '第三常购品类',

    -- === RFM客户分类模型 ===
    rfm_recency_score INT DEFAULT 0 COMMENT 'R分数(1-5): 最近购买时间',
    rfm_frequency_score INT DEFAULT 0 COMMENT 'F分数(1-5): 购买频次',
    rfm_monetary_score INT DEFAULT 0 COMMENT 'M分数(1-5): 消费金额',
    rfm_segment VARCHAR(50) COMMENT 'RFM客户分类',

    -- === 情绪与意图分析 ===
    sentiment_label VARCHAR(20) COMMENT '整体情绪标签: Positive/Neutral/Negative',
    sentiment_score DECIMAL(3,2) COMMENT '情绪分数(0-1)',
    dominant_intent VARCHAR(50) COMMENT '主要意图',
    pre_sale_score INT DEFAULT 0 COMMENT '售前热度(0-100)',
    post_sale_score INT DEFAULT 0 COMMENT '售后需求(0-100)',
    complaint_tendency VARCHAR(10) COMMENT '投诉倾向: 高/中/低',

    -- === 运营标签 ===
    follow_priority VARCHAR(10) COMMENT '跟进优先级: 紧急/高/中/低',

    -- === 元数据 ===
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- === 索引 ===
    INDEX idx_buyer_type (buyer_type),
    INDEX idx_channel (channel),
    INDEX idx_client_monthly_tag (client_monthly_tag),
    INDEX idx_vip_level (vip_level),
    INDEX idx_last_purchase (last_purchase_date),
    INDEX idx_churn_risk (churn_risk),
    INDEX idx_updated (updated_at),
    INDEX idx_l6m_netsales (l6m_netsales),
    INDEX idx_l1y_netsales (l1y_netsales),
    INDEX idx_rolling_24m_gmv (rolling_24m_gmv),
    INDEX idx_rfm_segment (rfm_segment),
    INDEX idx_sentiment (sentiment_label),
    INDEX idx_intent (dominant_intent),
    INDEX idx_follow_priority (follow_priority)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='目标买家预计算表 - 每天上午11点更新';

-- ============================================
-- 步骤2: 识别目标买家(Smoker + VIC)
-- ============================================

-- 2.1 创建临时表存储目标买家名单
DROP TEMPORARY TABLE IF EXISTS tmp_target_buyers;

CREATE TEMPORARY TABLE tmp_target_buyers (
    buyer_nick VARCHAR(255) PRIMARY KEY,
    is_smoker BOOLEAN,
    is_vic BOOLEAN,
    buyer_type VARCHAR(50)
);

-- 2.2 识别Smoker买家(购买过Pipes或Lighters品类)
INSERT INTO tmp_target_buyers (buyer_nick, is_smoker, is_vic, buyer_type)
SELECT DISTINCT
    买家昵称 as buyer_nick,
    TRUE as is_smoker,
    FALSE as is_vic,
    'SMOKER' as buyer_type
FROM dunhill_t01_trade_line
WHERE category IN ('Pipes', 'Lighters')
  AND 买家昵称 IS NOT NULL
  AND 买家昵称 != '';

-- 2.3 识别VIC买家(Rolling 24个月净销售 >= 30K)
INSERT INTO tmp_target_buyers (buyer_nick, is_smoker, is_vic, buyer_type)
SELECT DISTINCT
    买家昵称 as buyer_nick,
    FALSE as is_smoker,
    TRUE as is_vic,
    'VIC' as buyer_type
FROM dunhill_t01_trade_line
WHERE 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 24 MONTH)
  AND 买家昵称 IS NOT NULL
  AND 买家昵称 != ''
GROUP BY 买家昵称
HAVING SUM(成交总金额 - IFNULL(退款金额, 0)) >= 30000
ON DUPLICATE KEY UPDATE
    is_vic = TRUE,
    buyer_type = 'BOTH';

-- ============================================
-- 步骤3: 初始化数据(一次性执行)
-- ============================================

-- 3.1 插入目标买家的历史指标数据
INSERT INTO target_buyers_precomputed (
    buyer_nick,
    channel,
    buyer_type,
    is_smoker,
    is_vic,
    client_monthly_tag,
    historical_gmv,
    historical_refund,
    historical_net_sales,
    total_orders,
    first_purchase_date,
    last_purchase_date,
    rolling_24m_gmv,
    rolling_24m_netsales,
    rolling_24m_orders,
    rolling_24m_net_orders,
    l6m_netsales,
    l6m_gmv,
    l6m_orders,
    l6m_refund_rate,
    l1y_netsales,
    l1y_gmv,
    l1y_orders,
    l1y_refund_rate,
    city
)
SELECT
    tb.buyer_nick,
    COALESCE(MAX(CASE WHEN t.channel IS NOT NULL THEN t.channel END), 'PFS') as channel,
    tb.buyer_type,
    tb.is_smoker,
    tb.is_vic,
    MAX(t.client_monthly_tag) as client_monthly_tag,
    SUM(t.成交总金额) as historical_gmv,
    SUM(IFNULL(t.退款金额, 0)) as historical_refund,
    SUM(t.成交总金额 - IFNULL(t.退款金额, 0)) as historical_net_sales,
    COUNT(DISTINCT t.订单号) as total_orders,
    MIN(t.最后付款时间) as first_purchase_date,
    MAX(t.最后付款时间) as last_purchase_date,
    SUM(CASE
        WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 24 MONTH)
        THEN t.成交总金额
        ELSE 0
    END) as rolling_24m_gmv,
    SUM(CASE
        WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 24 MONTH)
        THEN (t.成交总金额 - IFNULL(t.退款金额, 0))
        ELSE 0
    END) as rolling_24m_netsales,
    COUNT(DISTINCT CASE
        WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 24 MONTH)
        THEN t.订单号
    END) as rolling_24m_orders,
    COUNT(DISTINCT CASE
        WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 24 MONTH)
        THEN t.订单号
    END) - COUNT(DISTINCT CASE
        WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 24 MONTH)
          AND t.退款金额 > 0
        THEN t.订单号
    END) as rolling_24m_net_orders,
    SUM(CASE
        WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
        THEN (t.成交总金额 - IFNULL(t.退款金额, 0))
        ELSE 0
    END) as l6m_netsales,
    SUM(CASE
        WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
        THEN t.成交总金额
        ELSE 0
    END) as l6m_gmv,
    COUNT(DISTINCT CASE
        WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
        THEN t.订单号
    END) as l6m_orders,
    0 as l6m_refund_rate,
    SUM(CASE
        WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
        THEN (t.成交总金额 - IFNULL(t.退款金额, 0))
        ELSE 0
    END) as l1y_netsales,
    SUM(CASE
        WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
        THEN t.成交总金额
        ELSE 0
    END) as l1y_gmv,
    COUNT(DISTINCT CASE
        WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
        THEN t.订单号
    END) as l1y_orders,
    0 as l1y_refund_rate,
    MAX(t.城市) as city
FROM tmp_target_buyers tb
JOIN dunhill_t01_trade_line t ON tb.buyer_nick = t.买家昵称
GROUP BY tb.buyer_nick, tb.buyer_type, tb.is_smoker, tb.is_vic;

-- 3.2 更新有效订单数、退款率和购买频率
UPDATE target_buyers_precomputed
SET
    total_net_orders = total_orders - (
        SELECT COUNT(DISTINCT 订单号)
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 = target_buyers_precomputed.buyer_nick
          AND 退款金额 > 0
    ),
    refund_rate = CASE
        WHEN historical_gmv > 0 THEN historical_refund / historical_gmv
        ELSE 0
    END,
    l6m_refund_rate = CASE
        WHEN l6m_gmv > 0 THEN
            (SELECT SUM(IFNULL(退款金额, 0))
             FROM dunhill_t01_trade_line
             WHERE 买家昵称 = target_buyers_precomputed.buyer_nick
               AND 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 6 MONTH)) / l6m_gmv
        ELSE 0
    END,
    l1y_refund_rate = CASE
        WHEN l1y_gmv > 0 THEN
            (SELECT SUM(IFNULL(退款金额, 0))
             FROM dunhill_t01_trade_line
             WHERE 买家昵称 = target_buyers_precomputed.buyer_nick
               AND 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 12 MONTH)) / l1y_gmv
        ELSE 0
    END,
    avg_purchase_interval_days = CASE
        WHEN total_orders > 0 AND DATEDIFF(last_purchase_date, first_purchase_date) > 0
        THEN DATEDIFF(last_purchase_date, first_purchase_date) / total_orders
        ELSE 0
    END;

-- 3.3 计算VIP等级
UPDATE target_buyers_precomputed
SET vip_level = CASE
    WHEN rolling_24m_netsales >= 450000 THEN 'V3'
    WHEN rolling_24m_netsales >= 150000 THEN 'V2'
    WHEN rolling_24m_netsales >= 50000 THEN 'V1'
    WHEN rolling_24m_netsales >= 30000 THEN 'V0'
    ELSE 'Non-VIP'
END;

-- 3.4 计算折扣敏感度
UPDATE target_buyers_precomputed
SET
    discount_ratio = (
        SELECT COALESCE(
            CAST(SUM(CASE WHEN FP_MD = 'MD' THEN 1 ELSE 0 END) AS DECIMAL(10,2)) /
            NULLIF(COUNT(DISTINCT 订单号), 0),
            0)
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 = target_buyers_precomputed.buyer_nick
    ),
    discount_sensitivity = CASE
        WHEN discount_ratio >= 0.7 THEN '高度敏感'
        WHEN discount_ratio >= 0.4 THEN '中度敏感'
        ELSE '低度敏感'
    END;

-- 3.5 更新聊天指标
UPDATE target_buyers_precomputed tb
SET
    chat_frequency_days = (
        SELECT COUNT(DISTINCT DATE(msg_time))
        FROM chat_history
        WHERE user_nick = tb.buyer_nick
    ),
    total_chat_messages = (
        SELECT COUNT(*)
        FROM chat_history
        WHERE user_nick = tb.buyer_nick
          AND sender_nick = tb.buyer_nick
    ),
    first_chat_date = (
        SELECT MIN(msg_time)
        FROM chat_history
        WHERE user_nick = tb.buyer_nick
    ),
    last_chat_date = (
        SELECT MAX(msg_time)
        FROM chat_history
        WHERE user_nick = tb.buyer_nick
    ),
    l30d_chat_frequency_days = (
        SELECT COUNT(DISTINCT DATE(msg_time))
        FROM chat_history
        WHERE user_nick = tb.buyer_nick
          AND msg_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    ),
    l3m_chat_frequency_days = (
        SELECT COUNT(DISTINCT DATE(msg_time))
        FROM chat_history
        WHERE user_nick = tb.buyer_nick
          AND msg_time >= DATE_SUB(NOW(), INTERVAL 3 MONTH)
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

-- 3.6 计算流失风险
UPDATE target_buyers_precomputed
SET churn_risk = CASE
    WHEN
        DATEDIFF(NOW(), last_purchase_date) > 730  -- 2年无复购
        AND DATEDIFF(NOW(), last_chat_date) > 180  -- 6个月无咨询
    THEN '高'
    WHEN
        DATEDIFF(NOW(), last_purchase_date) > 180  -- 6个月无复购
        OR DATEDIFF(NOW(), last_chat_date) > 90   -- 3个月无咨询
    THEN '中'
    ELSE '低'
END;

-- 3.7 更新品类偏好(TOP3) - 按NetSales排序
WITH buyer_category_stats AS (
    SELECT
        买家昵称,
        category,
        COUNT(DISTINCT 子订单号) as category_orders,
        SUM(成交总金额 - IFNULL(退款金额, 0)) as category_netsales
    FROM dunhill_t01_trade_line
    WHERE category IS NOT NULL AND category != ''
      AND 买家昵称 IS NOT NULL AND 买家昵称 != ''
    GROUP BY 买家昵称, category
),
ranked_categories AS (
    SELECT
        买家昵称,
        category,
        ROW_NUMBER() OVER (PARTITION BY 买家昵称 ORDER BY category_netsales DESC) as rank_num
    FROM buyer_category_stats
    WHERE 买家昵称 IN (SELECT buyer_nick FROM tmp_target_buyers)
)
UPDATE target_buyers_precomputed tb
LEFT JOIN (
    SELECT
        买家昵称,
        MAX(CASE WHEN rank_num = 1 THEN category END) as top_category,
        MAX(CASE WHEN rank_num = 2 THEN category END) as second_category,
        MAX(CASE WHEN rank_num = 3 THEN category END) as third_category
    FROM ranked_categories
    GROUP BY 买家昵称
) cats ON tb.buyer_nick = cats.买家昵称
SET
    tb.top_category = COALESCE(cats.top_category, 'Unknown'),
    tb.second_category = cats.second_category,
    tb.third_category = cats.third_category;

-- ============================================
-- 步骤4: 创建定时更新存储过程
-- ============================================

DROP PROCEDURE IF EXISTS refresh_target_buyers_precomputed;

DELIMITER $$

CREATE PROCEDURE refresh_target_buyers_precomputed()
BEGIN
    DECLARE start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    DECLARE affected_rows INT DEFAULT 0;
    DECLARE target_count INT DEFAULT 0;

    -- 记录开始
    SELECT CONCAT('🚀 开始刷新目标买家预计算表: ', start_time) AS message;

    -- 4.1 重新识别目标买家
    DROP TEMPORARY TABLE IF EXISTS tmp_target_buyers_new;

    CREATE TEMPORARY TABLE tmp_target_buyers_new (
        buyer_nick VARCHAR(255) PRIMARY KEY,
        is_smoker BOOLEAN,
        is_vic BOOLEAN,
        buyer_type VARCHAR(50)
    );

    -- Smoker买家
    INSERT INTO tmp_target_buyers_new (buyer_nick, is_smoker, is_vic, buyer_type)
    SELECT DISTINCT
        买家昵称,
        TRUE,
        FALSE,
        'SMOKER'
    FROM dunhill_t01_trade_line
    WHERE category IN ('Pipes', 'Lighters')
      AND 买家昵称 IS NOT NULL AND 买家昵称 != '';

    -- VIC买家
    INSERT INTO tmp_target_buyers_new (buyer_nick, is_smoker, is_vic, buyer_type)
    SELECT DISTINCT
        买家昵称,
        FALSE,
        TRUE,
        'VIC'
    FROM dunhill_t01_trade_line
    WHERE 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 24 MONTH)
      AND 买家昵称 IS NOT NULL AND 买家昵称 != ''
    GROUP BY 买家昵称
    HAVING SUM(成交总金额 - IFNULL(退款金额, 0)) >= 30000
    ON DUPLICATE KEY UPDATE
        is_vic = TRUE,
        buyer_type = 'BOTH';

    SET target_count = (SELECT COUNT(*) FROM tmp_target_buyers_new);

    -- 4.2 删除不再符合条件的买家
    DELETE FROM target_buyers_precomputed
    WHERE buyer_nick NOT IN (SELECT buyer_nick FROM tmp_target_buyers_new);
    SET affected_rows = ROW_COUNT();

    SELECT CONCAT('🗑️  删除了 ', affected_rows, ' 个不再符合条件的买家') AS message;

    -- 4.3 更新现有买家数据
    UPDATE target_buyers_precomputed tb
    INNER JOIN (
        SELECT
            tb.buyer_nick,
            tb.buyer_type,
            tb.is_smoker,
            tb.is_vic,
            MAX(t.client_monthly_tag) as client_monthly_tag,
            SUM(t.成交总金额) as historical_gmv,
            SUM(IFNULL(t.退款金额, 0)) as historical_refund,
            SUM(t.成交总金额 - IFNULL(t.退款金额, 0)) as historical_net_sales,
            COUNT(DISTINCT t.订单号) as total_orders,
            MIN(t.最后付款时间) as first_purchase_date,
            MAX(t.最后付款时间) as last_purchase_date,
            SUM(CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 24 MONTH) THEN t.成交总金额 ELSE 0 END) as rolling_24m_gmv,
            SUM(CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 24 MONTH) THEN (t.成交总金额 - IFNULL(t.退款金额, 0)) ELSE 0 END) as rolling_24m_netsales,
            COUNT(DISTINCT CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 24 MONTH) THEN t.订单号 END) as rolling_24m_orders,
            SUM(CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 6 MONTH) THEN (t.成交总金额 - IFNULL(t.退款金额, 0)) ELSE 0 END) as l6m_netsales,
            SUM(CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 6 MONTH) THEN t.成交总金额 ELSE 0 END) as l6m_gmv,
            COUNT(DISTINCT CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 6 MONTH) THEN t.订单号 END) as l6m_orders,
            SUM(CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 12 MONTH) THEN (t.成交总金额 - IFNULL(t.退款金额, 0)) ELSE 0 END) as l1y_netsales,
            SUM(CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 12 MONTH) THEN t.成交总金额 ELSE 0 END) as l1y_gmv,
            COUNT(DISTINCT CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 12 MONTH) THEN t.订单号 END) as l1y_orders,
            MAX(t.城市) as city,
            MAX(CASE WHEN t.channel IS NOT NULL THEN t.channel END) as channel
        FROM tmp_target_buyers_new tb
        JOIN dunhill_t01_trade_line t ON tb.buyer_nick = t.买家昵称
        GROUP BY tb.buyer_nick, tb.buyer_type, tb.is_smoker, tb.is_vic
    ) new_data ON tb.buyer_nick = new_data.buyer_nick
    SET
        tb.channel = new_data.channel,
        tb.buyer_type = new_data.buyer_type,
        tb.is_smoker = new_data.is_smoker,
        tb.is_vic = new_data.is_vic,
        tb.client_monthly_tag = new_data.client_monthly_tag,
        tb.historical_gmv = new_data.historical_gmv,
        tb.historical_refund = new_data.historical_refund,
        tb.historical_net_sales = new_data.historical_net_sales,
        tb.total_orders = new_data.total_orders,
        tb.first_purchase_date = new_data.first_purchase_date,
        tb.last_purchase_date = new_data.last_purchase_date,
        tb.rolling_24m_gmv = new_data.rolling_24m_gmv,
        tb.rolling_24m_netsales = new_data.rolling_24m_netsales,
        tb.rolling_24m_orders = new_data.rolling_24m_orders,
        tb.l6m_netsales = new_data.l6m_netsales,
        tb.l6m_gmv = new_data.l6m_gmv,
        tb.l6m_orders = new_data.l6m_orders,
        tb.l1y_netsales = new_data.l1y_netsales,
        tb.l1y_gmv = new_data.l1y_gmv,
        tb.l1y_orders = new_data.l1y_orders,
        tb.city = new_data.city,
        tb.updated_at = CURRENT_TIMESTAMP;

    SET affected_rows = ROW_COUNT();
    SELECT CONCAT('📝 更新了 ', affected_rows, ' 个现有买家') AS message;

    -- 4.4 插入新买家
    INSERT INTO target_buyers_precomputed (
        buyer_nick,
        channel,
        buyer_type,
        is_smoker,
        is_vic,
        client_monthly_tag,
        historical_gmv,
        historical_refund,
        historical_net_sales,
        total_orders,
        first_purchase_date,
        last_purchase_date,
        rolling_24m_gmv,
        rolling_24m_netsales,
        rolling_24m_orders,
        l6m_netsales,
        l6m_gmv,
        l6m_orders,
        l1y_netsales,
        l1y_gmv,
        l1y_orders,
        city
    )
    SELECT
        tb.buyer_nick,
        COALESCE(MAX(CASE WHEN t.channel IS NOT NULL THEN t.channel END), 'PFS'),
        tb.buyer_type,
        tb.is_smoker,
        tb.is_vic,
        MAX(t.client_monthly_tag),
        SUM(t.成交总金额),
        SUM(IFNULL(t.退款金额, 0)),
        SUM(t.成交总金额 - IFNULL(t.退款金额, 0)),
        COUNT(DISTINCT t.订单号),
        MIN(t.最后付款时间),
        MAX(t.最后付款时间),
        SUM(CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 24 MONTH) THEN t.成交总金额 ELSE 0 END),
        SUM(CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 24 MONTH) THEN (t.成交总金额 - IFNULL(t.退款金额, 0)) ELSE 0 END),
        COUNT(DISTINCT CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 24 MONTH) THEN t.订单号 END),
        SUM(CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 6 MONTH) THEN (t.成交总金额 - IFNULL(t.退款金额, 0)) ELSE 0 END),
        SUM(CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 6 MONTH) THEN t.成交总金额 ELSE 0 END),
        COUNT(DISTINCT CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 6 MONTH) THEN t.订单号 END),
        SUM(CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 12 MONTH) THEN (t.成交总金额 - IFNULL(t.退款金额, 0)) ELSE 0 END),
        SUM(CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 12 MONTH) THEN t.成交总金额 ELSE 0 END),
        COUNT(DISTINCT CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 12 MONTH) THEN t.订单号 END),
        MAX(t.城市)
    FROM tmp_target_buyers_new tb
    JOIN dunhill_t01_trade_line t ON tb.buyer_nick = t.买家昵称
    WHERE tb.buyer_nick NOT IN (SELECT buyer_nick FROM target_buyers_precomputed)
    GROUP BY tb.buyer_nick, tb.buyer_type, tb.is_smoker, tb.is_vic;

    SET affected_rows = ROW_COUNT();
    SELECT CONCAT('➕ 新增了 ', affected_rows, ' 个目标买家') AS message;

    -- 4.5 重新计算所有派生字段
    -- 有效订单数、净订单数、退款率和购买频率
    UPDATE target_buyers_precomputed
    SET
        total_net_orders = total_orders - (
            SELECT COUNT(DISTINCT 订单号)
            FROM dunhill_t01_trade_line
            WHERE 买家昵称 = target_buyers_precomputed.buyer_nick
              AND 退款金额 > 0
        ),
        rolling_24m_net_orders = rolling_24m_orders - (
            SELECT COUNT(DISTINCT 订单号)
            FROM dunhill_t01_trade_line
            WHERE 买家昵称 = target_buyers_precomputed.buyer_nick
              AND 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 24 MONTH)
              AND 退款金额 > 0
        ),
        refund_rate = CASE
            WHEN historical_gmv > 0 THEN historical_refund / historical_gmv
            ELSE 0
        END,
        l6m_refund_rate = CASE
            WHEN l6m_gmv > 0 THEN
                (SELECT SUM(IFNULL(退款金额, 0))
                 FROM dunhill_t01_trade_line
                 WHERE 买家昵称 = target_buyers_precomputed.buyer_nick
                   AND 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 6 MONTH)) / l6m_gmv
            ELSE 0
        END,
        l1y_refund_rate = CASE
            WHEN l1y_gmv > 0 THEN
                (SELECT SUM(IFNULL(退款金额, 0))
                 FROM dunhill_t01_trade_line
                 WHERE 买家昵称 = target_buyers_precomputed.buyer_nick
                   AND 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 12 MONTH)) / l1y_gmv
            ELSE 0
        END,
        avg_purchase_interval_days = CASE
            WHEN total_orders > 0 AND DATEDIFF(last_purchase_date, first_purchase_date) > 0
            THEN DATEDIFF(last_purchase_date, first_purchase_date) / total_orders
            ELSE 0
        END;

    -- VIP等级
    UPDATE target_buyers_precomputed
    SET vip_level = CASE
        WHEN rolling_24m_netsales >= 450000 THEN 'V3'
        WHEN rolling_24m_netsales >= 150000 THEN 'V2'
        WHEN rolling_24m_netsales >= 50000 THEN 'V1'
        WHEN rolling_24m_netsales >= 30000 THEN 'V0'
        ELSE 'Non-VIP'
    END;

    -- 折扣敏感度
    UPDATE target_buyers_precomputed
    SET
        discount_ratio = (
            SELECT COALESCE(
                CAST(SUM(CASE WHEN FP_MD = 'MD' THEN 1 ELSE 0 END) AS DECIMAL(10,2)) /
                NULLIF(COUNT(DISTINCT 订单号), 0),
                0)
            FROM dunhill_t01_trade_line
            WHERE 买家昵称 = target_buyers_precomputed.buyer_nick
        ),
        discount_sensitivity = CASE
            WHEN discount_ratio >= 0.7 THEN '高度敏感'
            WHEN discount_ratio >= 0.4 THEN '中度敏感'
            ELSE '低度敏感'
        END;

    -- 聊天指标
    UPDATE target_buyers_precomputed tb
    SET
        chat_frequency_days = (
            SELECT COUNT(DISTINCT DATE(msg_time))
            FROM chat_history
            WHERE user_nick = tb.buyer_nick
        ),
        total_chat_messages = (
            SELECT COUNT(*)
            FROM chat_history
            WHERE user_nick = tb.buyer_nick
        ),
        first_chat_date = (
            SELECT MIN(msg_time)
            FROM chat_history
            WHERE user_nick = tb.buyer_nick
        ),
        last_chat_date = (
            SELECT MAX(msg_time)
            FROM chat_history
            WHERE user_nick = tb.buyer_nick
        ),
        l30d_chat_frequency_days = (
            SELECT COUNT(DISTINCT DATE(msg_time))
            FROM chat_history
            WHERE user_nick = tb.buyer_nick
              AND msg_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        ),
        l3m_chat_frequency_days = (
            SELECT COUNT(DISTINCT DATE(msg_time))
            FROM chat_history
            WHERE user_nick = tb.buyer_nick
              AND msg_time >= DATE_SUB(NOW(), INTERVAL 3 MONTH)
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

    -- 流失风险
    UPDATE target_buyers_precomputed
    SET churn_risk = CASE
        WHEN
            DATEDIFF(NOW(), last_purchase_date) > 730
            AND DATEDIFF(NOW(), last_chat_date) > 180
        THEN '高'
        WHEN
            DATEDIFF(NOW(), last_purchase_date) > 180
            OR DATEDIFF(NOW(), last_chat_date) > 90
        THEN '中'
        ELSE '低'
    END;

    -- 品类偏好(TOP3) - 按NetSales排序
    WITH buyer_category_stats AS (
        SELECT
            买家昵称,
            category,
            COUNT(DISTINCT 子订单号) as category_orders,
            SUM(成交总金额 - IFNULL(退款金额, 0)) as category_netsales
        FROM dunhill_t01_trade_line
        WHERE category IS NOT NULL AND category != ''
          AND 买家昵称 IS NOT NULL AND 买家昵称 != ''
        GROUP BY 买家昵称, category
    ),
    ranked_categories AS (
        SELECT
            买家昵称,
            category,
            ROW_NUMBER() OVER (PARTITION BY 买家昵称 ORDER BY category_netsales DESC) as rank_num
        FROM buyer_category_stats
        WHERE 买家昵称 IN (SELECT buyer_nick FROM tmp_target_buyers_new)
    )
    UPDATE target_buyers_precomputed tb
    LEFT JOIN (
        SELECT
            买家昵称,
            MAX(CASE WHEN rank_num = 1 THEN category END) as top_category,
            MAX(CASE WHEN rank_num = 2 THEN category END) as second_category,
            MAX(CASE WHEN rank_num = 3 THEN category END) as third_category
        FROM ranked_categories
        GROUP BY 买家昵称
    ) cats ON tb.buyer_nick = cats.买家昵称
    SET
        tb.top_category = COALESCE(cats.top_category, 'Unknown'),
        tb.second_category = cats.second_category,
        tb.third_category = cats.third_category;

    -- 清理临时表
    DROP TEMPORARY TABLE IF EXISTS tmp_target_buyers_new;

    -- 输出统计信息
    SELECT CONCAT('✅ 刷新完成！') AS message;
    SELECT CONCAT('🎯 目标买家总数: ', target_count) AS target_count;
    SELECT CONCAT('📊 当前表中买家数: ', (SELECT COUNT(*) FROM target_buyers_precomputed)) AS total_buyers;
    SELECT CONCAT('⏱️  总耗时: ', TIMESTAMPDIFF(SECOND, start_time, CURRENT_TIMESTAMP), ' 秒') AS duration;
    SELECT CONCAT('🕒 最后更新时间: ', CURRENT_TIMESTAMP) AS last_updated;

    -- 按类型统计
    SELECT
        buyer_type,
        COUNT(*) as count,
        AVG(rolling_24m_netsales) as avg_rolling_netsales
    FROM target_buyers_precomputed
    GROUP BY buyer_type
    ORDER BY count DESC;

END$$

DELIMITER ;

-- ============================================
-- 步骤5: 创建定时事件(每天上午11点执行)
-- ============================================

-- 启用事件调度器 (需要SUPER权限, 如果已启用可跳过)
-- SET GLOBAL event_scheduler = ON;

-- 删除旧事件(如果存在)
DROP EVENT IF EXISTS event_refresh_target_buyers;

-- 创建新事件
CREATE EVENT event_refresh_target_buyers
ON SCHEDULE EVERY 1 DAY
STARTS CONCAT(CURDATE() + INTERVAL 1 DAY, ' 11:00:00')
COMMENT '每天上午11点刷新目标买家预计算表'
DO
CALL refresh_target_buyers_precomputed();

-- ============================================
-- 步骤6: 查询示例
-- ============================================

-- 1. 手动触发更新(测试用)
-- CALL refresh_target_buyers_precomputed();

-- 2. 查看所有目标买家(超快!)
-- SELECT * FROM target_buyers_precomputed ORDER BY last_purchase_date DESC LIMIT 100;

-- 3. 按买家类型筛选
-- SELECT buyer_nick, vip_level, rolling_24m_netsales, l6m_spend
-- FROM target_buyers_precomputed
-- WHERE buyer_type = 'SMOKER'
-- ORDER BY rolling_24m_netsales DESC;

-- 4. 查看流失风险高的买家
-- SELECT buyer_nick, vip_level, churn_risk, last_purchase_date, last_chat_date
-- FROM target_buyers_precomputed
-- WHERE churn_risk = '高'
-- ORDER BY last_purchase_date;

-- 5. 按VIP等级统计
-- SELECT
--     vip_level,
--     COUNT(*) as count,
--     SUM(historical_net_sales) as total_netsales
-- FROM target_buyers_precomputed
-- GROUP BY vip_level
-- ORDER BY rolling_24m_netsales DESC;

-- 6. 按渠道统计
-- SELECT
--     channel,
--     COUNT(*) as count,
--     AVG(rolling_24m_netsales) as avg_netsales
-- FROM target_buyers_precomputed
-- GROUP BY channel;

-- ============================================
-- 验证和监控
-- ============================================

-- 查看事件调度器状态
-- SHOW VARIABLES LIKE 'event_scheduler';

-- 查看所有事件
-- SHOW EVENTS;

-- 查看下一次执行时间
-- SELECT * FROM information_schema.EVENTS WHERE EVENT_NAME = 'event_refresh_target_buyers';
