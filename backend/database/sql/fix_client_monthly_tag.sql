-- 修正client_monthly_tag获取逻辑
-- 应该获取每个买家最近一条购买记录对应的client_monthly_tag

-- 先删除旧的存储过程
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
    -- 使用CTE获取每个买家最近购买记录的client_monthly_tag
    UPDATE target_buyers_precomputed tb
    INNER JOIN (
        SELECT
            tb_buyer.buyer_nick,
            tb_buyer.buyer_type,
            tb_buyer.is_smoker,
            tb_buyer.is_vic,
            latest_tags.client_monthly_tag,
            SUM(t.成交总金额) as historical_gmv,
            SUM(IFNULL(t.退款金额, 0)) as historical_refund,
            SUM(t.成交总金额 - IFNULL(t.退款金额, 0)) as historical_net_sales,
            COUNT(DISTINCT t.订单号) as total_orders,
            MIN(t.最后付款时间) as first_purchase_date,
            MAX(t.最后付款时间) as last_purchase_date,
            SUM(CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 24 MONTH) THEN (t.成交总金额 - IFNULL(t.退款金额, 0)) ELSE 0 END) as rolling_24m_netsales,
            COUNT(DISTINCT CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 24 MONTH) THEN t.订单号 END) as rolling_24m_orders,
            SUM(CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 6 MONTH) THEN (t.成交总金额 - IFNULL(t.退款金额, 0)) ELSE 0 END) as l6m_spend,
            COUNT(DISTINCT CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 6 MONTH) THEN t.订单号 END) as l6m_orders,
            SUM(CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 12 MONTH) THEN (t.成交总金额 - IFNULL(t.退款金额, 0)) ELSE 0 END) as l1y_spend,
            COUNT(DISTINCT CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 12 MONTH) THEN t.订单号 END) as l1y_orders,
            MAX(t.城市) as city,
            MAX(CASE WHEN t.channel IS NOT NULL THEN t.channel END) as channel
        FROM tmp_target_buyers_new tb_buyer
        JOIN dunhill_t01_trade_line t ON tb_buyer.buyer_nick = t.买家昵称
        INNER JOIN (
            -- 获取每个买家最近购买记录的client_monthly_tag
            SELECT
                买家昵称,
                client_monthly_tag
            FROM (
                SELECT
                    买家昵称,
                    client_monthly_tag,
                    ROW_NUMBER() OVER (PARTITION BY 买家昵称 ORDER BY 最后付款时间 DESC) as rn
                FROM dunhill_t01_trade_line
                WHERE 买家昵称 IN (SELECT buyer_nick FROM tmp_target_buyers_new)
            ) ranked
            WHERE rn = 1
        ) latest_tags ON tb_buyer.buyer_nick = latest_tags.买家昵称
        GROUP BY tb_buyer.buyer_nick, tb_buyer.buyer_type, tb_buyer.is_smoker, tb_buyer.is_vic, latest_tags.client_monthly_tag
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
        tb.rolling_24m_netsales = new_data.rolling_24m_netsales,
        tb.rolling_24m_orders = new_data.rolling_24m_orders,
        tb.l6m_spend = new_data.l6m_spend,
        tb.l6m_orders = new_data.l6m_orders,
        tb.l1y_spend = new_data.l1y_spend,
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
        rolling_24m_netsales,
        rolling_24m_orders,
        l6m_spend,
        l6m_orders,
        l1y_spend,
        l1y_orders,
        city
    )
    SELECT
        tb_buyer.buyer_nick,
        COALESCE(MAX(CASE WHEN t.channel IS NOT NULL THEN t.channel END), 'PFS'),
        tb_buyer.buyer_type,
        tb_buyer.is_smoker,
        tb_buyer.is_vic,
        latest_tags.client_monthly_tag,
        SUM(t.成交总金额),
        SUM(IFNULL(t.退款金额, 0)),
        SUM(t.成交总金额 - IFNULL(t.退款金额, 0)),
        COUNT(DISTINCT t.订单号),
        MIN(t.最后付款时间),
        MAX(t.最后付款时间),
        SUM(CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 24 MONTH) THEN (t.成交总金额 - IFNULL(t.退款金额, 0)) ELSE 0 END),
        COUNT(DISTINCT CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 24 MONTH) THEN t.订单号 END),
        SUM(CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 6 MONTH) THEN (t.成交总金额 - IFNULL(t.退款金额, 0)) ELSE 0 END),
        COUNT(DISTINCT CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 6 MONTH) THEN t.订单号 END),
        SUM(CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 12 MONTH) THEN (t.成交总金额 - IFNULL(t.退款金额, 0)) ELSE 0 END),
        COUNT(DISTINCT CASE WHEN t.最后付款时间 >= DATE_SUB(NOW(), INTERVAL 12 MONTH) THEN t.订单号 END),
        MAX(t.城市)
    FROM tmp_target_buyers_new tb_buyer
    JOIN dunhill_t01_trade_line t ON tb_buyer.buyer_nick = t.买家昵称
    INNER JOIN (
        -- 获取每个买家最近购买记录的client_monthly_tag
        SELECT
            买家昵称,
            client_monthly_tag
        FROM (
            SELECT
                买家昵称,
                client_monthly_tag,
                ROW_NUMBER() OVER (PARTITION BY 买家昵称 ORDER BY 最后付款时间 DESC) as rn
            FROM dunhill_t01_trade_line
            WHERE 买家昵称 IN (SELECT buyer_nick FROM tmp_target_buyers_new)
        ) ranked
        WHERE rn = 1
    ) latest_tags ON tb_buyer.buyer_nick = latest_tags.买家昵称
    WHERE tb_buyer.buyer_nick NOT IN (SELECT buyer_nick FROM target_buyers_precomputed)
    GROUP BY tb_buyer.buyer_nick, tb_buyer.buyer_type, tb_buyer.is_smoker, tb_buyer.is_vic, latest_tags.client_monthly_tag;

    SET affected_rows = ROW_COUNT();
    SELECT CONCAT('➕ 新增了 ', affected_rows, ' 个目标买家') AS message;

    -- 4.5 重新计算所有派生字段
    -- 有效订单数和退款率
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
        last_chat_date = (
            SELECT MAX(msg_time)
            FROM chat_history
            WHERE user_nick = tb.buyer_nick
        ),
        l3m_chat_frequency_days = (
            SELECT COUNT(DISTINCT DATE(msg_time))
            FROM chat_history
            WHERE user_nick = tb.buyer_nick
              AND msg_time >= DATE_SUB(NOW(), INTERVAL 3 MONTH)
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

    -- 品类偏好(TOP3)
    WITH buyer_category_stats AS (
        SELECT
            买家昵称,
            category,
            COUNT(DISTINCT 子订单号) as category_orders,
            SUM(成交总金额 - IFNULL(退款金额, 0)) as category_spend
        FROM dunhill_t01_trade_line
        WHERE category IS NOT NULL AND category != ''
          AND 买家昵称 IS NOT NULL AND 买家昵称 != ''
        GROUP BY 买家昵称, category
    ),
    ranked_categories AS (
        SELECT
            买家昵称,
            category,
            ROW_NUMBER() OVER (PARTITION BY 买家昵称 ORDER BY category_orders DESC) as rank_num
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
