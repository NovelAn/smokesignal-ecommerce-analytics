CREATE DEFINER=`novelan`@`%` PROCEDURE `dunhill`.`refresh_target_buyers_precomputed`()
BEGIN
    DECLARE start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    DECLARE affected_rows INT DEFAULT 0;
    DECLARE target_count INT DEFAULT 0;

    SELECT CONCAT('🚀 开始刷新目标买家预计算表: ', start_time) AS message;

    -- ============================================
    -- Phase 1: 识别目标买家
    -- ============================================
    DROP TEMPORARY TABLE IF EXISTS tmp_target_buyers_new;
    CREATE TEMPORARY TABLE tmp_target_buyers_new (
        buyer_nick VARCHAR(255) PRIMARY KEY,
        is_smoker BOOLEAN,
        is_vic BOOLEAN,
        buyer_type VARCHAR(50)
    );

    INSERT INTO tmp_target_buyers_new (buyer_nick, is_smoker, is_vic, buyer_type)
    SELECT DISTINCT 买家昵称, TRUE, FALSE, 'SMOKER'
    FROM dunhill_t01_trade_line
    WHERE category IN ('Pipes', 'Lighters')
      AND 买家昵称 IS NOT NULL AND 买家昵称 != '';

    INSERT INTO tmp_target_buyers_new (buyer_nick, is_smoker, is_vic, buyer_type)
    SELECT DISTINCT 买家昵称, FALSE, TRUE, 'VIC'
    FROM dunhill_t01_trade_line
    WHERE 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 24 MONTH)
      AND 买家昵称 IS NOT NULL AND 买家昵称 != ''
    GROUP BY 买家昵称
    HAVING SUM(成交总金额 - IFNULL(退款金额, 0)) >= 30000
    ON DUPLICATE KEY UPDATE is_vic = TRUE, buyer_type = 'BOTH';

    -- 1c. 当季主推买家（近3个月购买了当前活跃主推商品，已有 VIC/Smoker 自动跳过）
    INSERT IGNORE INTO tmp_target_buyers_new (buyer_nick, is_smoker, is_vic, buyer_type)
    SELECT DISTINCT t.买家昵称, FALSE, FALSE, 'SEASON'
    FROM dunhill_t01_trade_line t
    INNER JOIN season_products sp ON t.skc = sp.skc AND sp.is_active = 1
    WHERE t.买家昵称 IS NOT NULL AND t.买家昵称 != ''
      AND t.付款时间 IS NOT NULL
      AND t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 3 MONTH);

    -- 1d. 大单买家（近3个月单笔 >= 3件 且 >= ¥20,000，已有 VIC/Smoker/Season 自动跳过）
    INSERT IGNORE INTO tmp_target_buyers_new (buyer_nick, is_smoker, is_vic, buyer_type)
    SELECT 买家昵称, FALSE, FALSE, 'BULK'
    FROM (
        SELECT 买家昵称
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 IS NOT NULL AND 买家昵称 != ''
          AND 付款时间 IS NOT NULL
          AND 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 3 MONTH)
        GROUP BY 买家昵称, 订单号
        HAVING SUM(件数) >= 3 AND SUM(成交总金额) >= 20000
    ) bulk_buyers;

    SET target_count = (SELECT COUNT(*) FROM tmp_target_buyers_new);

    -- ============================================
    -- Phase 2: 清理 + 基础数据更新/插入
    -- ============================================
    DELETE FROM target_buyers_precomputed
    WHERE buyer_nick NOT IN (SELECT buyer_nick FROM tmp_target_buyers_new);
    SET affected_rows = ROW_COUNT();
    SELECT CONCAT('🗑️  删除了 ', affected_rows, ' 个不再符合条件的买家') AS message;

    -- 最新 client_monthly_tag
    DROP TEMPORARY TABLE IF EXISTS tmp_latest_tags;
    CREATE TEMPORARY TABLE tmp_latest_tags (buyer_nick VARCHAR(255) PRIMARY KEY, client_monthly_tag VARCHAR(50));
    INSERT INTO tmp_latest_tags (buyer_nick, client_monthly_tag)
    SELECT 买家昵称, client_monthly_tag
    FROM (
        SELECT 买家昵称, client_monthly_tag,
               ROW_NUMBER() OVER (PARTITION BY 买家昵称 ORDER BY 最后付款时间 DESC) as rn
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 IN (SELECT buyer_nick FROM tmp_target_buyers_new)
    ) ranked WHERE rn = 1;

    -- 更新现有买家
    UPDATE target_buyers_precomputed tb
    INNER JOIN (
        SELECT
            tb2.buyer_nick, tb2.buyer_type, tb2.is_smoker, tb2.is_vic,
            latest.client_monthly_tag,
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
        FROM tmp_target_buyers_new tb2
        JOIN dunhill_t01_trade_line t ON tb2.buyer_nick = t.买家昵称
        JOIN tmp_latest_tags latest ON tb2.buyer_nick = latest.buyer_nick
        GROUP BY tb2.buyer_nick, tb2.buyer_type, tb2.is_smoker, tb2.is_vic, latest.client_monthly_tag
    ) new_data ON tb.buyer_nick = new_data.buyer_nick
    SET
        tb.channel = new_data.channel, tb.buyer_type = new_data.buyer_type,
        tb.is_smoker = new_data.is_smoker, tb.is_vic = new_data.is_vic,
        tb.client_monthly_tag = new_data.client_monthly_tag,
        tb.historical_gmv = new_data.historical_gmv, tb.historical_refund = new_data.historical_refund,
        tb.historical_net_sales = new_data.historical_net_sales, tb.total_orders = new_data.total_orders,
        tb.first_purchase_date = new_data.first_purchase_date, tb.last_purchase_date = new_data.last_purchase_date,
        tb.rolling_24m_gmv = new_data.rolling_24m_gmv, tb.rolling_24m_netsales = new_data.rolling_24m_netsales,
        tb.rolling_24m_orders = new_data.rolling_24m_orders,
        tb.l6m_netsales = new_data.l6m_netsales, tb.l6m_gmv = new_data.l6m_gmv, tb.l6m_orders = new_data.l6m_orders,
        tb.l1y_netsales = new_data.l1y_netsales, tb.l1y_gmv = new_data.l1y_gmv, tb.l1y_orders = new_data.l1y_orders,
        tb.city = new_data.city, tb.updated_at = CURRENT_TIMESTAMP;
    SET affected_rows = ROW_COUNT();
    SELECT CONCAT('📝 更新了 ', affected_rows, ' 个现有买家') AS message;

    -- 插入新买家
    INSERT INTO target_buyers_precomputed (
        buyer_nick, channel, buyer_type, is_smoker, is_vic, client_monthly_tag,
        historical_gmv, historical_refund, historical_net_sales, total_orders,
        first_purchase_date, last_purchase_date,
        rolling_24m_gmv, rolling_24m_netsales, rolling_24m_orders,
        l6m_netsales, l6m_gmv, l6m_orders, l1y_netsales, l1y_gmv, l1y_orders, city
    )
    SELECT
        tb2.buyer_nick,
        COALESCE(MAX(CASE WHEN t.channel IS NOT NULL THEN t.channel END), 'PFS'),
        tb2.buyer_type, tb2.is_smoker, tb2.is_vic, latest.client_monthly_tag,
        SUM(t.成交总金额), SUM(IFNULL(t.退款金额, 0)),
        SUM(t.成交总金额 - IFNULL(t.退款金额, 0)), COUNT(DISTINCT t.订单号),
        MIN(t.最后付款时间), MAX(t.最后付款时间),
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
    FROM tmp_target_buyers_new tb2
    JOIN dunhill_t01_trade_line t ON tb2.buyer_nick = t.买家昵称
    JOIN tmp_latest_tags latest ON tb2.buyer_nick = latest.buyer_nick
    WHERE tb2.buyer_nick NOT IN (SELECT buyer_nick FROM target_buyers_precomputed)
    GROUP BY tb2.buyer_nick, tb2.buyer_type, tb2.is_smoker, tb2.is_vic, latest.client_monthly_tag;
    SET affected_rows = ROW_COUNT();
    SELECT CONCAT('➕ 新增了 ', affected_rows, ' 个目标买家') AS message;

    -- ============================================
    -- Phase 3: 批量聚合派生字段（替代 N+1 子查询）
    -- ============================================

    -- 3a. 退款 + 折扣指标（单次扫描 dunhill_t01_trade_line）
    DROP TEMPORARY TABLE IF EXISTS tmp_trade_derived;
    CREATE TEMPORARY TABLE tmp_trade_derived (
        buyer_nick VARCHAR(255) PRIMARY KEY,
        refund_orders INT,
        rolling_24m_refund_orders INT,
        l6m_refund DECIMAL(18,2),
        l1y_refund DECIMAL(18,2),
        discount_ratio DECIMAL(10,2)
    );
    INSERT INTO tmp_trade_derived
    SELECT
        买家昵称,
        COUNT(DISTINCT CASE WHEN 退款金额 > 0 THEN 订单号 END),
        COUNT(DISTINCT CASE WHEN 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 24 MONTH) AND 退款金额 > 0 THEN 订单号 END),
        SUM(CASE WHEN 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 6 MONTH) THEN IFNULL(退款金额, 0) ELSE 0 END),
        SUM(CASE WHEN 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 12 MONTH) THEN IFNULL(退款金额, 0) ELSE 0 END),
        COALESCE(CAST(SUM(CASE WHEN FP_MD = 'MD' THEN 1 ELSE 0 END) AS DECIMAL(10,2)) / NULLIF(COUNT(DISTINCT 子订单号), 0), 0)
    FROM dunhill_t01_trade_line
    WHERE 买家昵称 IN (SELECT buyer_nick FROM target_buyers_precomputed)
    GROUP BY 买家昵称;

    -- 3b. 聊天指标（单次扫描 chat_history）
    DROP TEMPORARY TABLE IF EXISTS tmp_chat_stats;
    CREATE TEMPORARY TABLE tmp_chat_stats (
        buyer_nick VARCHAR(255) PRIMARY KEY,
        chat_frequency_days INT,
        total_chat_messages INT,
        first_chat_date DATETIME,
        last_chat_date DATETIME,
        l30d_chat_frequency_days INT,
        l3m_chat_frequency_days INT,
        avg_chat_interval_days DECIMAL(10,1)
    );
    INSERT INTO tmp_chat_stats
    SELECT
        user_nick,
        COUNT(DISTINCT DATE(msg_time)),
        SUM(CASE WHEN sender_nick = user_nick THEN 1 ELSE 0 END),
        MIN(msg_time),
        MAX(msg_time),
        COUNT(DISTINCT CASE WHEN msg_time >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN DATE(msg_time) END),
        COUNT(DISTINCT CASE WHEN msg_time >= DATE_SUB(NOW(), INTERVAL 3 MONTH) THEN DATE(msg_time) END),
        CASE
            WHEN COUNT(DISTINCT DATE(msg_time)) <= 1 THEN 0
            ELSE DATEDIFF(MAX(DATE(msg_time)), MIN(DATE(msg_time))) / (COUNT(DISTINCT DATE(msg_time)) - 1)
        END
    FROM chat_history
    WHERE user_nick IN (SELECT buyer_nick FROM target_buyers_precomputed)
    GROUP BY user_nick;

    -- 3c. 主推系列指标
    DROP TEMPORARY TABLE IF EXISTS tmp_main_push_stats;
    CREATE TEMPORARY TABLE tmp_main_push_stats (
        buyer_nick VARCHAR(255) PRIMARY KEY,
        main_push_items INT,
        main_push_amount DECIMAL(18,2)
    );
    INSERT INTO tmp_main_push_stats
    SELECT
        t.买家昵称,
        SUM(t.件数),
        SUM(t.成交总金额)
    FROM dunhill_t01_trade_line t
    INNER JOIN season_products sp ON t.skc = sp.skc AND sp.is_active = 1
    WHERE t.买家昵称 IN (SELECT buyer_nick FROM target_buyers_precomputed)
      AND t.付款时间 IS NOT NULL
      AND t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 3 MONTH)
    GROUP BY t.买家昵称;

    -- 3d. 大单指标
    DROP TEMPORARY TABLE IF EXISTS tmp_bulk_stats;
    CREATE TEMPORARY TABLE tmp_bulk_stats (
        buyer_nick VARCHAR(255) PRIMARY KEY,
        bulk_order_count INT,
        max_bulk_amount DECIMAL(18,2)
    );
    INSERT INTO tmp_bulk_stats
    SELECT 买家昵称, COUNT(*), MAX(order_total)
    FROM (
        SELECT 买家昵称, SUM(成交总金额) AS order_total
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 IN (SELECT buyer_nick FROM target_buyers_precomputed)
          AND 付款时间 IS NOT NULL
          AND 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 3 MONTH)
        GROUP BY 买家昵称, 订单号
        HAVING SUM(件数) >= 3 AND SUM(成交总金额) >= 20000
    ) bulk_orders
    GROUP BY 买家昵称;

    -- ============================================
    -- Phase 4: 一次性 JOIN 更新所有派生字段
    -- ============================================

    -- 4a. 退款 + 折扣 + 购买间隔
    UPDATE target_buyers_precomputed tb
    LEFT JOIN tmp_trade_derived r ON tb.buyer_nick = r.buyer_nick
    SET
        tb.total_net_orders = tb.total_orders - IFNULL(r.refund_orders, 0),
        tb.rolling_24m_net_orders = tb.rolling_24m_orders - IFNULL(r.rolling_24m_refund_orders, 0),
        tb.refund_rate = CASE WHEN tb.historical_gmv > 0 THEN tb.historical_refund / tb.historical_gmv ELSE 0 END,
        tb.l6m_refund_rate = CASE WHEN tb.l6m_gmv > 0 THEN IFNULL(r.l6m_refund, 0) / tb.l6m_gmv ELSE 0 END,
        tb.l1y_refund_rate = CASE WHEN tb.l1y_gmv > 0 THEN IFNULL(r.l1y_refund, 0) / tb.l1y_gmv ELSE 0 END,
        tb.avg_purchase_interval_days = CASE
            WHEN tb.total_orders > 0 AND DATEDIFF(tb.last_purchase_date, tb.first_purchase_date) > 0
            THEN DATEDIFF(tb.last_purchase_date, tb.first_purchase_date) / tb.total_orders
            ELSE 0
        END,
        tb.discount_ratio = IFNULL(r.discount_ratio, 0),
        tb.discount_sensitivity = CASE
            WHEN IFNULL(r.discount_ratio, 0) >= 0.7 THEN '高度敏感'
            WHEN IFNULL(r.discount_ratio, 0) >= 0.4 THEN '中度敏感'
            ELSE '低度敏感'
        END;

    -- 4b. 聊天指标
    UPDATE target_buyers_precomputed tb
    LEFT JOIN tmp_chat_stats c ON tb.buyer_nick = c.buyer_nick
    SET
        tb.chat_frequency_days = IFNULL(c.chat_frequency_days, 0),
        tb.total_chat_messages = IFNULL(c.total_chat_messages, 0),
        tb.first_chat_date = c.first_chat_date,
        tb.last_chat_date = c.last_chat_date,
        tb.l30d_chat_frequency_days = IFNULL(c.l30d_chat_frequency_days, 0),
        tb.l3m_chat_frequency_days = IFNULL(c.l3m_chat_frequency_days, 0),
        tb.avg_chat_interval_days = IFNULL(c.avg_chat_interval_days, 0);

    -- 4c. 流失风险
    UPDATE target_buyers_precomputed
    SET churn_risk = CASE
        WHEN DATEDIFF(NOW(), last_purchase_date) > 730 AND DATEDIFF(NOW(), last_chat_date) > 180 THEN '高'
        WHEN DATEDIFF(NOW(), last_purchase_date) > 180 AND DATEDIFF(NOW(), last_chat_date) > 90 THEN '中'
        ELSE '低'
    END;

    -- 4d. 品类偏好
    WITH buyer_category_stats AS (
        SELECT 买家昵称, category,
               COUNT(DISTINCT 子订单号) as category_orders,
               SUM(成交总金额 - IFNULL(退款金额, 0)) as category_netsales
        FROM dunhill_t01_trade_line
        WHERE category IS NOT NULL AND category != '' AND 买家昵称 IS NOT NULL AND 买家昵称 != ''
        GROUP BY 买家昵称, category
    ),
    ranked_categories AS (
        SELECT 买家昵称, category,
               ROW_NUMBER() OVER (PARTITION BY 买家昵称 ORDER BY category_netsales DESC) as rank_num
        FROM buyer_category_stats
        WHERE 买家昵称 IN (SELECT buyer_nick FROM tmp_target_buyers_new)
    )
    UPDATE target_buyers_precomputed tb
    LEFT JOIN (
        SELECT 买家昵称,
               MAX(CASE WHEN rank_num = 1 THEN category END) as top_category,
               MAX(CASE WHEN rank_num = 2 THEN category END) as second_category,
               MAX(CASE WHEN rank_num = 3 THEN category END) as third_category
        FROM ranked_categories GROUP BY 买家昵称
    ) cats ON tb.buyer_nick = cats.买家昵称
    SET
        tb.top_category = COALESCE(cats.top_category, 'Unknown'),
        tb.second_category = cats.second_category,
        tb.third_category = cats.third_category;

    -- 4e. 主推系列 + 大单买家
    UPDATE target_buyers_precomputed tb
    LEFT JOIN tmp_main_push_stats mp ON tb.buyer_nick = mp.buyer_nick
    LEFT JOIN tmp_bulk_stats bk ON tb.buyer_nick = bk.buyer_nick
    SET
        tb.main_push_items = IFNULL(mp.main_push_items, 0),
        tb.main_push_amount = IFNULL(mp.main_push_amount, 0),
        tb.is_main_push_buyer = IFNULL(mp.main_push_items, 0) > 0,
        tb.bulk_order_count = IFNULL(bk.bulk_order_count, 0),
        tb.max_bulk_amount = IFNULL(bk.max_bulk_amount, 0),
        tb.is_bulk_buyer = IFNULL(bk.bulk_order_count, 0) > 0;

    SELECT CONCAT('🏷️ 派生字段计算完成') AS message;

    -- ============================================
    -- Phase 5: RFM 分类 + VIP + 优先级（纯字段计算，无子查询）
    -- ============================================

    -- 5a. RFM 得分 + VIP 等级（合并为单条 UPDATE）
    UPDATE target_buyers_precomputed
    SET
        rfm_recency_score = CASE
            WHEN last_purchase_date IS NULL THEN 0
            WHEN DATEDIFF(NOW(), last_purchase_date) <= 60 THEN 5
            WHEN DATEDIFF(NOW(), last_purchase_date) <= 180 THEN 4
            WHEN DATEDIFF(NOW(), last_purchase_date) <= 365 THEN 3
            WHEN DATEDIFF(NOW(), last_purchase_date) <= 730 THEN 2
            ELSE 1
        END,
        rfm_frequency_score = CASE
            WHEN total_orders >= 5 THEN 5
            WHEN total_orders >= 3 THEN 4
            WHEN total_orders = 2 THEN 3
            WHEN total_orders = 1 AND chat_frequency_days > 0 THEN 2
            WHEN total_orders = 1 THEN 1
            ELSE 0
        END,
        rfm_monetary_score = CASE
            WHEN historical_net_sales >= 50000 THEN 5
            WHEN historical_net_sales >= 20000 THEN 4
            WHEN historical_net_sales >= 10000 THEN 3
            WHEN historical_net_sales >= 5000 THEN 2
            ELSE 1
        END,
        vip_level = CASE
            WHEN rolling_24m_netsales >= 450000 THEN 'V3'
            WHEN rolling_24m_netsales >= 150000 THEN 'V2'
            WHEN rolling_24m_netsales >= 50000 THEN 'V1'
            WHEN rolling_24m_netsales >= 30000 THEN 'V0'
            ELSE 'Non-VIP'
        END;

    -- 5b. RFM 客户分群
    UPDATE target_buyers_precomputed
    SET rfm_segment = CASE
        WHEN rfm_monetary_score >= 4 AND rfm_recency_score >= 4 AND rfm_frequency_score >= 4 THEN '重要价值客户'
        WHEN rfm_monetary_score >= 4 AND rfm_recency_score >= 4 AND rfm_frequency_score <= 3 THEN '重要发展客户'
        WHEN rfm_monetary_score >= 4 AND rfm_recency_score <= 3 AND rfm_frequency_score >= 4 THEN '重要保持客户'
        WHEN rfm_monetary_score >= 4 AND rfm_recency_score <= 3 AND rfm_frequency_score <= 3 THEN '重要挽留客户'
        WHEN rfm_monetary_score = 3 AND rfm_recency_score >= 4 AND rfm_frequency_score >= 4 THEN '优质价值客户'
        WHEN rfm_monetary_score = 3 AND rfm_recency_score >= 4 AND rfm_frequency_score <= 3 THEN '优质发展客户'
        WHEN rfm_monetary_score = 3 AND rfm_recency_score <= 3 AND rfm_frequency_score >= 4 THEN '优质保持客户'
        WHEN rfm_monetary_score = 3 AND rfm_recency_score <= 3 AND rfm_frequency_score <= 3 THEN '优质挽留客户'
        WHEN rfm_monetary_score = 2 AND rfm_recency_score >= 4 THEN '潜力客户'
        WHEN rfm_monetary_score = 2 AND rfm_recency_score <= 3 THEN '待激活客户'
        WHEN rfm_monetary_score = 1 AND rfm_recency_score >= 4 THEN '新客户'
        WHEN rfm_monetary_score = 1 AND rfm_recency_score IN (2, 3) THEN '低价值客户'
        WHEN rfm_recency_score = 1 THEN '已流失'
        WHEN rfm_recency_score = 0 THEN '无购买记录'
    END;

    -- 5c. 跟进优先级（基础 + 所有升级条件合并为单条 CASE）
    UPDATE target_buyers_precomputed
    SET follow_priority = CASE
        -- 基础优先级（基于 RFM 分群）
        WHEN rfm_segment IN ('重要价值客户', '重要保持客户', '重要挽留客户') THEN '紧急'
        WHEN rfm_segment IN ('重要发展客户', '优质价值客户', '优质发展客户', '优质保持客户', '优质挽留客户') THEN '高'
        WHEN rfm_segment IN ('潜力客户', '待激活客户', '新客户') THEN '中'
        WHEN rfm_segment IN ('低价值客户', '已流失', '无购买记录') THEN '低'
        ELSE '中'
    END;

    SELECT CONCAT('📊 RFM分类完成') AS message;

    -- ============================================
    -- Phase 6: 同步 AI 分析结果
    -- ============================================
    UPDATE target_buyers_precomputed tb
    INNER JOIN buyer_ai_analysis_cache cache ON tb.buyer_nick = cache.buyer_nick
    SET
        tb.sentiment_label = cache.sentiment_label,
        tb.sentiment_score = cache.sentiment_score,
        tb.dominant_intent = cache.dominant_intent
    WHERE cache.sentiment_score IS NOT NULL;
    SELECT CONCAT('📊 同步了 ', ROW_COUNT(), ' 条AI分析结果') AS message;

    -- ============================================
    -- Phase 6b: 优先级升级（必须在 AI 同步之后，依赖 sentiment_label）
    -- ============================================
    UPDATE target_buyers_precomputed
    SET follow_priority = CASE
        -- P1: 负面情感 → 紧急（最高优先，需立即关注）
        WHEN sentiment_label = 'Negative' THEN '紧急'
        -- P2: 高流失风险 → 紧急
        WHEN churn_risk = '高' AND follow_priority IN ('中', '低') THEN '紧急'
        -- P3: 近3个月主推系列买家（低优先→高）
        WHEN is_main_push_buyer = TRUE AND follow_priority = '低'
             AND last_purchase_date >= DATE_SUB(NOW(), INTERVAL 3 MONTH) THEN '高'
        -- P4: VIP V3/V2（中优先→高）
        WHEN vip_level IN ('V3', 'V2') AND follow_priority = '中' THEN '高'
        -- P5: 近3个月大单买家（低优先→中）
        WHEN is_bulk_buyer = TRUE AND follow_priority = '低'
             AND last_purchase_date >= DATE_SUB(NOW(), INTERVAL 3 MONTH) THEN '中'
        ELSE follow_priority
    END;

    -- ============================================
    -- Phase 7: 清理 + 统计
    -- ============================================
    DROP TEMPORARY TABLE IF EXISTS tmp_target_buyers_new;
    DROP TEMPORARY TABLE IF EXISTS tmp_latest_tags;
    DROP TEMPORARY TABLE IF EXISTS tmp_trade_derived;
    DROP TEMPORARY TABLE IF EXISTS tmp_chat_stats;
    DROP TEMPORARY TABLE IF EXISTS tmp_main_push_stats;
    DROP TEMPORARY TABLE IF EXISTS tmp_bulk_stats;

    SELECT CONCAT('✅ 刷新完成！') AS message;
    SELECT CONCAT('🎯 目标买家总数: ', target_count) AS target_count;
    SELECT CONCAT('📊 当前表中买家数: ', (SELECT COUNT(*) FROM target_buyers_precomputed)) AS total_buyers;
    SELECT CONCAT('⏱️  总耗时: ', TIMESTAMPDIFF(SECOND, start_time, CURRENT_TIMESTAMP), ' 秒') AS duration;
    SELECT CONCAT('🕒 最后更新时间: ', CURRENT_TIMESTAMP) AS last_updated;

    SELECT
        buyer_type,
        COUNT(*) as count,
        AVG(rolling_24m_netsales) as avg_rolling_netsales
    FROM target_buyers_precomputed
    GROUP BY buyer_type
    ORDER BY count DESC;

END
