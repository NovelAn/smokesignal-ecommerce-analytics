CREATE DEFINER=`novelan`@`%` PROCEDURE `dunhill`.`refresh_target_buyers_precomputed`()
BEGIN
    DECLARE start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    DECLARE affected_rows INT DEFAULT 0;
    DECLARE target_count INT DEFAULT 0;

    
    SELECT CONCAT('🚀 开始刷新目标买家预计算表: ', start_time) AS message;

    
    DROP TEMPORARY TABLE IF EXISTS tmp_target_buyers_new;

    CREATE TEMPORARY TABLE tmp_target_buyers_new (
        buyer_nick VARCHAR(255) PRIMARY KEY,
        is_smoker BOOLEAN,
        is_vic BOOLEAN,
        buyer_type VARCHAR(50)
    );

    
    INSERT INTO tmp_target_buyers_new (buyer_nick, is_smoker, is_vic, buyer_type)
    SELECT DISTINCT
        买家昵称,
        TRUE,
        FALSE,
        'SMOKER'
    FROM dunhill_t01_trade_line
    WHERE category IN ('Pipes', 'Lighters')
      AND 买家昵称 IS NOT NULL AND 买家昵称 != '';

    
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

    
    DELETE FROM target_buyers_precomputed
    WHERE buyer_nick NOT IN (SELECT buyer_nick FROM tmp_target_buyers_new);
    SET affected_rows = ROW_COUNT();

    SELECT CONCAT('🗑️  删除了 ', affected_rows, ' 个不再符合条件的买家') AS message;

    -- 4.3 创建临时表存储每个买家最近购买记录的client_monthly_tag
    DROP TEMPORARY TABLE IF EXISTS tmp_latest_tags;

    CREATE TEMPORARY TABLE tmp_latest_tags (
        buyer_nick VARCHAR(255) PRIMARY KEY,
        client_monthly_tag VARCHAR(50)
    );

    INSERT INTO tmp_latest_tags (buyer_nick, client_monthly_tag)
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
    WHERE rn = 1;

    -- 4.4 更新现有买家数据
    UPDATE target_buyers_precomputed tb
    INNER JOIN (
        SELECT
            tb.buyer_nick,
            tb.buyer_type,
            tb.is_smoker,
            tb.is_vic,
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
        FROM tmp_target_buyers_new tb
        JOIN dunhill_t01_trade_line t ON tb.buyer_nick = t.买家昵称
        JOIN tmp_latest_tags latest ON tb.buyer_nick = latest.buyer_nick
        GROUP BY tb.buyer_nick, tb.buyer_type, tb.is_smoker, tb.is_vic, latest.client_monthly_tag
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

    -- 4.5 插入新买家
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
        latest.client_monthly_tag,
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
    JOIN tmp_latest_tags latest ON tb.buyer_nick = latest.buyer_nick
    WHERE tb.buyer_nick NOT IN (SELECT buyer_nick FROM target_buyers_precomputed)
    GROUP BY tb.buyer_nick, tb.buyer_type, tb.is_smoker, tb.is_vic, latest.client_monthly_tag;

    SET affected_rows = ROW_COUNT();
    SELECT CONCAT('➕ 新增了 ', affected_rows, ' 个目标买家') AS message;

    -- 4.6 重新计算所有派生字段
    
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

    
    UPDATE target_buyers_precomputed
    SET vip_level = CASE
        WHEN rolling_24m_netsales >= 450000 THEN 'V3'
        WHEN rolling_24m_netsales >= 150000 THEN 'V2'
        WHEN rolling_24m_netsales >= 50000 THEN 'V1'
        WHEN rolling_24m_netsales >= 30000 THEN 'V0'
        ELSE 'Non-VIP'
    END;

    
    UPDATE target_buyers_precomputed
    SET
        discount_ratio = (
            SELECT COALESCE(
                CAST(SUM(CASE WHEN FP_MD = 'MD' THEN 1 ELSE 0 END) AS DECIMAL(10,2)) /
                NULLIF(COUNT(DISTINCT 子订单号), 0),
                0)
            FROM dunhill_t01_trade_line
            WHERE 买家昵称 = target_buyers_precomputed.buyer_nick
        ),
        discount_sensitivity = CASE
            WHEN discount_ratio >= 0.7 THEN '高度敏感'
            WHEN discount_ratio >= 0.4 THEN '中度敏感'
            ELSE '低度敏感'
        END;

    
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

    -- ============================================
    -- RFM Customer Classification Calculation
    -- ============================================

    -- Calculate R Score (Recency - days since last purchase)
    -- Luxury thresholds: 60d/180d/365d/730d
    UPDATE target_buyers_precomputed
    SET rfm_recency_score = CASE
        WHEN last_purchase_date IS NULL THEN 0
        WHEN DATEDIFF(NOW(), last_purchase_date) <= 60 THEN 5
        WHEN DATEDIFF(NOW(), last_purchase_date) <= 180 THEN 4
        WHEN DATEDIFF(NOW(), last_purchase_date) <= 365 THEN 3
        WHEN DATEDIFF(NOW(), last_purchase_date) <= 730 THEN 2
        ELSE 1
    END;

    -- Calculate F Score (Frequency - total orders)
    -- Luxury thresholds: 5+/3-4/2/1+chat/1
    UPDATE target_buyers_precomputed
    SET rfm_frequency_score = CASE
        WHEN total_orders >= 5 THEN 5
        WHEN total_orders >= 3 THEN 4
        WHEN total_orders = 2 THEN 3
        WHEN total_orders = 1 AND chat_frequency_days > 0 THEN 2
        WHEN total_orders = 1 THEN 1
        ELSE 0
    END;

    -- Calculate M Score (Monetary - historical net sales)
    -- Luxury thresholds: 50K/20K/10K/5K
    UPDATE target_buyers_precomputed
    SET rfm_monetary_score = CASE
        WHEN historical_net_sales >= 50000 THEN 5
        WHEN historical_net_sales >= 20000 THEN 4
        WHEN historical_net_sales >= 10000 THEN 3
        WHEN historical_net_sales >= 5000 THEN 2
        ELSE 1
    END;

    -- ============================================
    -- Determine RFM Segment (Simplified - 11 categories)
    -- 奢品男装行业优化分类，    -- ============================================

    UPDATE target_buyers_precomputed
    SET rfm_segment = CASE
        -- ============================================
        -- M≥4 (≥20K) - 高价值客户群 (核心VIP)
        -- ============================================
        -- 重要价值客户: 活跃+高频+高消费 → 核心VIP
        WHEN rfm_monetary_score >= 4 AND rfm_recency_score >= 4 AND rfm_frequency_score >= 4
            THEN '重要价值客户'
        -- 重要发展客户: 活跃+低频+高消费 → 提升复购频次
        WHEN rfm_monetary_score >= 4 AND rfm_recency_score >= 4 AND rfm_frequency_score <= 3
            THEN '重要发展客户'
        -- 重要保持客户: 不活跃+高频+高消费 → 召回维护
        WHEN rfm_monetary_score >= 4 AND rfm_recency_score <= 3 AND rfm_frequency_score >= 4
            THEN '重要保持客户'
        -- 重要挽留客户: 不活跃+低频+高消费 → 紧急挽回
        WHEN rfm_monetary_score >= 4 AND rfm_recency_score <= 3 AND rfm_frequency_score <= 3
            THEN '重要挽留客户'

        -- ============================================
        -- M=3 (10K-20K) - 中高价值客户群
        -- ============================================
        -- 优质价值客户: 活跃+高频+中消费 → 重点培养
        WHEN rfm_monetary_score = 3 AND rfm_recency_score >= 4 AND rfm_frequency_score >= 4
            THEN '优质价值客户'
        -- 优质发展客户: 活跃+低频+中消费 → 促进复购
        WHEN rfm_monetary_score = 3 AND rfm_recency_score >= 4 AND rfm_frequency_score <= 3
            THEN '优质发展客户'
        -- 优质保持客户: 不活跃+高频+中消费 → 持续维护
        WHEN rfm_monetary_score = 3 AND rfm_recency_score <= 3 AND rfm_frequency_score >= 4
            THEN '优质保持客户'
        -- 优质挽留客户: 不活跃+低频+中消费 → 激活召回
        WHEN rfm_monetary_score = 3 AND rfm_recency_score <= 3 AND rfm_frequency_score <= 3
            THEN '优质挽留客户'

        -- ============================================
        -- M=2 (5K-10K) - 潜力客户群
        -- ============================================
        -- 潜力客户: 活跃 → 引导升级
        WHEN rfm_monetary_score = 2 AND rfm_recency_score >= 4
            THEN '潜力客户'
        -- 待激活客户: 不活跃 → 促销激活
        WHEN rfm_monetary_score = 2 AND rfm_recency_score <= 3
            THEN '待激活客户'

        -- ============================================
        -- M=1 (<5K) - 入门客户群
        -- ============================================
        -- 新客户: 活跃 → 培育转化
        WHEN rfm_monetary_score = 1 AND rfm_recency_score >= 4
            THEN '新客户'
        -- 低价值客户: 不活跃 → 低优先级
        WHEN rfm_monetary_score = 1 AND rfm_recency_score IN (2, 3)
            THEN '低价值客户'

        -- ============================================
        -- 特殊情况
        -- ============================================
        -- 已流失: R=1 (超过2年无购买)
        WHEN rfm_recency_score = 1
            THEN '已流失'
        -- 无购买记录: R=0
        WHEN rfm_recency_score = 0
            THEN '无购买记录'
    END;

    -- ============================================
    -- Calculate Follow-up Priority
    -- 基于RFM分类的跟进优先级
    -- ============================================

    UPDATE target_buyers_precomputed
    SET follow_priority = CASE
        -- 紧急: 核心VIP
        WHEN rfm_segment IN ('重要价值客户', '重要保持客户', '重要挽留客户') THEN '紧急'
        -- 高: 高价值客户群
        WHEN rfm_segment IN ('重要发展客户', '优质价值客户', '优质发展客户', '优质保持客户', '优质挽留客户') THEN '高'
        -- 中: 潜力客户
        WHEN rfm_segment IN ('潜力客户', '待激活客户', '新客户') THEN '中'
        -- 低: 低价值客户和已流失
        WHEN rfm_segment IN ('低价值客户', '已流失', '无购买记录') THEN '低'
        ELSE '中'
    END;

    -- Upgrade priority for high churn risk
    UPDATE target_buyers_precomputed
    SET follow_priority = '高'
    WHERE churn_risk = '高' AND follow_priority IN ('中', '低');

    -- Upgrade priority for VIP customers
    UPDATE target_buyers_precomputed
    SET follow_priority = '高'
    WHERE vip_level IN ('V3', 'V2') AND follow_priority = '中';

    SELECT CONCAT('📊 RFM分类完成') AS message;

    -- ============================================
    -- 同步AI分析结果 (情感/意图)
    -- ============================================

    -- 从缓存表读取情感/意图分析结果
    UPDATE target_buyers_precomputed tb
    INNER JOIN buyer_ai_analysis_cache cache
        ON tb.buyer_nick = cache.buyer_nick
    SET
        tb.sentiment_label = cache.sentiment_label,
        tb.sentiment_score = cache.sentiment_score,
        tb.dominant_intent = cache.dominant_intent
    WHERE cache.sentiment_score IS NOT NULL;

    SELECT CONCAT('📊 同步了 ', ROW_COUNT(), ' 条AI分析结果') AS message;

    DROP TEMPORARY TABLE IF EXISTS tmp_target_buyers_new;
    DROP TEMPORARY TABLE IF EXISTS tmp_latest_tags;

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