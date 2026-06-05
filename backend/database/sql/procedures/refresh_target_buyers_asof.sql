-- ============================================
-- refresh_target_buyers_asof(d) procedure
-- ============================================
-- 用途：参数化重算历史某天 d 的 target_buyers_precomputed 真 ASOF 状态
--       并写入 target_buyers_precomputed_history
-- 关键：参数 d 替换主表 procedure 的 NOW()/CURDATE()，所有时间窗口基于 d
-- 场景：一次性 backfill 历史快照 (2025-04-01 起) + 异常补跑
-- 幂等：ON DUPLICATE KEY UPDATE 重跑不重复
-- 告警：本 procedure 不调 send_alert_email，由 Python 调用方处理（一次性脚本）
-- ============================================
-- 与 snapshot_target_buyers_history() 的关系：
--   snapshot_target_buyers_history() = refresh_target_buyers_asof(CURDATE()) + event
--   本 procedure 主体逻辑与 snapshot 完全相同，仅日期来源不同
--   任何对算法/字段的修改必须同步到两者（防漂移）
-- ============================================

DROP PROCEDURE IF EXISTS refresh_target_buyers_asof;

DELIMITER $$

CREATE PROCEDURE refresh_target_buyers_asof(IN p_asof_date DATE)
BEGIN
    DECLARE v_snapshot_date DATE DEFAULT p_asof_date;
    DECLARE v_target_count INT DEFAULT 0;
    DECLARE v_start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    DECLARE v_error_msg TEXT DEFAULT NULL;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        GET DIAGNOSTICS CONDITION 1 v_error_msg = MESSAGE_TEXT;
        -- 不调 send_alert_email: 一次性脚本, 由 Python 调用方处理告警
        -- 直接 RESIGNAL 让 Python 端捕获错误并重试/跳过
        RESIGNAL;
    END;

    -- 参数校验
    IF p_asof_date IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'p_asof_date cannot be NULL';
    END IF;

    IF p_asof_date > CURDATE() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'p_asof_date cannot be in the future';
    END IF;

    SELECT CONCAT('开始 refresh_asof, date=', v_snapshot_date) AS message;

    -- ============================================
    -- Step 1: 识别 d 当天的目标池子
    -- ============================================
    DROP TEMPORARY TABLE IF EXISTS tmp_target;
    CREATE TEMPORARY TABLE tmp_target (
        buyer_nick VARCHAR(255) PRIMARY KEY,
        is_smoker TINYINT(1),
        is_vic TINYINT(1),
        buyer_type VARCHAR(50)
    );

    -- Smoker: d 之前买过 Pipes/Lighters
    INSERT IGNORE INTO tmp_target (buyer_nick, is_smoker, is_vic, buyer_type)
    SELECT DISTINCT 买家昵称, 1, 0, 'SMOKER'
    FROM dunhill_t01_trade_line
    WHERE category IN ('Pipes', 'Lighters')
      AND 买家昵称 IS NOT NULL AND 买家昵称 != ''
      AND 最后付款时间 < v_snapshot_date;

    -- VIC: rolling 24M 净销售 >= 30K (基于 d)
    INSERT INTO tmp_target (buyer_nick, is_smoker, is_vic, buyer_type)
    SELECT 买家昵称, 0, 1, 'VIC'
    FROM dunhill_t01_trade_line
    WHERE 最后付款时间 < v_snapshot_date
      AND 最后付款时间 >= DATE_SUB(v_snapshot_date, INTERVAL 24 MONTH)
      AND 买家昵称 IS NOT NULL AND 买家昵称 != ''
    GROUP BY 买家昵称
    HAVING SUM(成交总金额 - IFNULL(退款金额, 0)) >= 30000
    ON DUPLICATE KEY UPDATE is_vic=1, buyer_type='BOTH';

    SET v_target_count = (SELECT COUNT(*) FROM tmp_target);
    SELECT CONCAT('目标池: ', v_target_count, ' 人 (asof=', v_snapshot_date, ')') AS message;

    -- ============================================
    -- Step 2: 计算 5 个时间窗口聚合 (全部基于 d)
    -- ============================================
    DROP TEMPORARY TABLE IF EXISTS tmp_cum;
    CREATE TEMPORARY TABLE tmp_cum (
        buyer_nick VARCHAR(255) PRIMARY KEY,
        channel VARCHAR(10),
        client_monthly_tag VARCHAR(50),
        city VARCHAR(100),
        first_purchase_date DATETIME,
        last_purchase_date DATETIME,
        historical_gmv DECIMAL(18,2),
        historical_refund DECIMAL(18,2),
        historical_net_sales DECIMAL(18,2),
        total_orders INT,
        refunded_orders INT
    );
    INSERT INTO tmp_cum
    SELECT
        买家昵称,
        MAX(CASE WHEN channel IS NOT NULL THEN channel END),
        MAX(client_monthly_tag),
        MAX(城市),
        MIN(最后付款时间),
        MAX(最后付款时间),
        SUM(成交总金额),
        SUM(IFNULL(退款金额, 0)),
        SUM(成交总金额 - IFNULL(退款金额, 0)),
        COUNT(DISTINCT 订单号),
        COUNT(DISTINCT CASE WHEN 退款金额 > 0 THEN 订单号 END)
    FROM dunhill_t01_trade_line
    WHERE 买家昵称 IN (SELECT buyer_nick FROM tmp_target)
      AND 最后付款时间 < v_snapshot_date
    GROUP BY 买家昵称;

    DROP TEMPORARY TABLE IF EXISTS tmp_r24;
    CREATE TEMPORARY TABLE tmp_r24 (
        buyer_nick VARCHAR(255) PRIMARY KEY,
        rolling_24m_gmv DECIMAL(18,2),
        rolling_24m_netsales DECIMAL(18,2),
        rolling_24m_orders INT,
        rolling_24m_refund DECIMAL(18,2)
    );
    INSERT INTO tmp_r24
    SELECT
        买家昵称,
        SUM(成交总金额),
        SUM(成交总金额 - IFNULL(退款金额, 0)),
        COUNT(DISTINCT 订单号),
        SUM(IFNULL(退款金额, 0))
    FROM dunhill_t01_trade_line
    WHERE 买家昵称 IN (SELECT buyer_nick FROM tmp_target)
      AND 最后付款时间 < v_snapshot_date
      AND 最后付款时间 >= DATE_SUB(v_snapshot_date, INTERVAL 24 MONTH)
    GROUP BY 买家昵称;

    DROP TEMPORARY TABLE IF EXISTS tmp_l6m;
    CREATE TEMPORARY TABLE tmp_l6m (
        buyer_nick VARCHAR(255) PRIMARY KEY,
        l6m_gmv DECIMAL(18,2),
        l6m_netsales DECIMAL(18,2),
        l6m_orders INT,
        l6m_refund DECIMAL(18,2)
    );
    INSERT INTO tmp_l6m
    SELECT
        买家昵称,
        SUM(成交总金额),
        SUM(成交总金额 - IFNULL(退款金额, 0)),
        COUNT(DISTINCT 订单号),
        SUM(IFNULL(退款金额, 0))
    FROM dunhill_t01_trade_line
    WHERE 买家昵称 IN (SELECT buyer_nick FROM tmp_target)
      AND 最后付款时间 < v_snapshot_date
      AND 最后付款时间 >= DATE_SUB(v_snapshot_date, INTERVAL 6 MONTH)
    GROUP BY 买家昵称;

    DROP TEMPORARY TABLE IF EXISTS tmp_l1y;
    CREATE TEMPORARY TABLE tmp_l1y (
        buyer_nick VARCHAR(255) PRIMARY KEY,
        l1y_gmv DECIMAL(18,2),
        l1y_netsales DECIMAL(18,2),
        l1y_orders INT,
        l1y_refund DECIMAL(18,2)
    );
    INSERT INTO tmp_l1y
    SELECT
        买家昵称,
        SUM(成交总金额),
        SUM(成交总金额 - IFNULL(退款金额, 0)),
        COUNT(DISTINCT 订单号),
        SUM(IFNULL(退款金额, 0))
    FROM dunhill_t01_trade_line
    WHERE 买家昵称 IN (SELECT buyer_nick FROM tmp_target)
      AND 最后付款时间 < v_snapshot_date
      AND 最后付款时间 >= DATE_SUB(v_snapshot_date, INTERVAL 12 MONTH)
    GROUP BY 买家昵称;

    DROP TEMPORARY TABLE IF EXISTS tmp_discount;
    CREATE TEMPORARY TABLE tmp_discount (
        buyer_nick VARCHAR(255) PRIMARY KEY,
        discount_ratio DECIMAL(5,2)
    );
    INSERT INTO tmp_discount
    SELECT
        买家昵称,
        CAST(SUM(CASE WHEN FP_MD = 'MD' THEN 1 ELSE 0 END) AS DECIMAL(10,2))
            / NULLIF(COUNT(DISTINCT 订单号), 0)
    FROM dunhill_t01_trade_line
    WHERE 买家昵称 IN (SELECT buyer_nick FROM tmp_target)
      AND 最后付款时间 < v_snapshot_date
    GROUP BY 买家昵称;

    DROP TEMPORARY TABLE IF EXISTS tmp_cat;
    CREATE TEMPORARY TABLE tmp_cat (
        buyer_nick VARCHAR(255),
        category VARCHAR(50),
        rank_num INT,
        PRIMARY KEY (buyer_nick, rank_num)
    );
    INSERT INTO tmp_cat
    SELECT buyer_nick, category, rank_num FROM (
        SELECT
            买家昵称 AS buyer_nick,
            category,
            SUM(成交总金额 - IFNULL(退款金额, 0)) AS cat_netsales,
            ROW_NUMBER() OVER (PARTITION BY 买家昵称 ORDER BY SUM(成交总金额 - IFNULL(退款金额, 0)) DESC) AS rank_num
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 IN (SELECT buyer_nick FROM tmp_target)
          AND 最后付款时间 < v_snapshot_date
          AND category IS NOT NULL AND category != ''
        GROUP BY 买家昵称, category
    ) ranked
    WHERE rank_num <= 3;

    -- ============================================
    -- Step 3: Final INSERT (CTE with R/F/M scores)
    -- ============================================
    INSERT INTO target_buyers_precomputed_history
        (buyer_nick, snapshot_date, channel, client_monthly_tag, is_smoker, is_vic,
         buyer_type, vip_level, historical_gmv, historical_refund, historical_net_sales,
         total_orders, total_net_orders, refund_rate,
         rolling_24m_gmv, rolling_24m_netsales, rolling_24m_orders, rolling_24m_net_orders,
         l6m_netsales, l6m_gmv, l6m_orders, l6m_refund_rate,
         l1y_netsales, l1y_gmv, l1y_orders, l1y_refund_rate,
         avg_purchase_interval_days, discount_ratio, discount_sensitivity,
         first_purchase_date, last_purchase_date, city,
         top_category, second_category, third_category,
         rfm_recency_score, rfm_frequency_score, rfm_monetary_score,
         rfm_segment, churn_risk)
    WITH base AS (
        SELECT
            t.buyer_nick,
            cum.channel,
            cum.client_monthly_tag,
            t.is_smoker,
            t.is_vic,
            t.buyer_type,
            CASE
                WHEN COALESCE(r24.rolling_24m_netsales, 0) >= 450000 THEN 'V3'
                WHEN COALESCE(r24.rolling_24m_netsales, 0) >= 150000 THEN 'V2'
                WHEN COALESCE(r24.rolling_24m_netsales, 0) >= 50000  THEN 'V1'
                WHEN COALESCE(r24.rolling_24m_netsales, 0) >= 30000  THEN 'V0'
                ELSE 'Non-VIP'
            END AS vip_level,
            COALESCE(cum.historical_gmv, 0) AS historical_gmv,
            COALESCE(cum.historical_refund, 0) AS historical_refund,
            COALESCE(cum.historical_net_sales, 0) AS historical_net_sales,
            COALESCE(cum.total_orders, 0) AS total_orders,
            COALESCE(cum.total_orders, 0) - COALESCE(cum.refunded_orders, 0) AS total_net_orders,
            CASE WHEN COALESCE(cum.historical_gmv, 0) > 0
                 THEN cum.historical_refund / cum.historical_gmv ELSE 0 END AS refund_rate,
            COALESCE(r24.rolling_24m_gmv, 0) AS rolling_24m_gmv,
            COALESCE(r24.rolling_24m_netsales, 0) AS rolling_24m_netsales,
            COALESCE(r24.rolling_24m_orders, 0) AS rolling_24m_orders,
            COALESCE(r24.rolling_24m_orders, 0) AS rolling_24m_net_orders,
            COALESCE(l6m.l6m_netsales, 0) AS l6m_netsales,
            COALESCE(l6m.l6m_gmv, 0) AS l6m_gmv,
            COALESCE(l6m.l6m_orders, 0) AS l6m_orders,
            CASE WHEN COALESCE(l6m.l6m_gmv, 0) > 0
                 THEN COALESCE(l6m.l6m_refund, 0) / l6m.l6m_gmv ELSE 0 END AS l6m_refund_rate,
            COALESCE(l1y.l1y_netsales, 0) AS l1y_netsales,
            COALESCE(l1y.l1y_gmv, 0) AS l1y_gmv,
            COALESCE(l1y.l1y_orders, 0) AS l1y_orders,
            CASE WHEN COALESCE(l1y.l1y_gmv, 0) > 0
                 THEN COALESCE(l1y.l1y_refund, 0) / l1y.l1y_gmv ELSE 0 END AS l1y_refund_rate,
            CASE WHEN COALESCE(cum.total_orders, 0) > 0
                      AND DATEDIFF(cum.last_purchase_date, cum.first_purchase_date) > 0
                 THEN DATEDIFF(cum.last_purchase_date, cum.first_purchase_date) / cum.total_orders
                 ELSE 0 END AS avg_purchase_interval_days,
            COALESCE(disc.discount_ratio, 0) AS discount_ratio,
            CASE
                WHEN COALESCE(disc.discount_ratio, 0) >= 0.7 THEN '高度敏感'
                WHEN COALESCE(disc.discount_ratio, 0) >= 0.4 THEN '中度敏感'
                ELSE '低度敏感'
            END AS discount_sensitivity,
            cum.first_purchase_date,
            cum.last_purchase_date,
            cum.city,
            cats.top_cat,
            cats.second_cat,
            cats.third_cat,
            -- R/F/M scores (与主表 procedure 同款阈值, ASOF 基于 d)
            CASE
                WHEN cum.last_purchase_date IS NULL THEN 0
                WHEN DATEDIFF(v_snapshot_date, cum.last_purchase_date) <= 60  THEN 5
                WHEN DATEDIFF(v_snapshot_date, cum.last_purchase_date) <= 180 THEN 4
                WHEN DATEDIFF(v_snapshot_date, cum.last_purchase_date) <= 365 THEN 3
                WHEN DATEDIFF(v_snapshot_date, cum.last_purchase_date) <= 730 THEN 2
                ELSE 1
            END AS r_score,
            CASE
                WHEN cum.total_orders >= 5 THEN 5
                WHEN cum.total_orders >= 3 THEN 4
                WHEN cum.total_orders = 2 THEN 3
                WHEN cum.total_orders = 1 THEN 1
                ELSE 0
            END AS f_score,
            CASE
                WHEN cum.historical_net_sales >= 50000 THEN 5
                WHEN cum.historical_net_sales >= 20000 THEN 4
                WHEN cum.historical_net_sales >= 10000 THEN 3
                WHEN cum.historical_net_sales >= 5000  THEN 2
                ELSE 1
            END AS m_score
        FROM tmp_target t
        LEFT JOIN tmp_cum cum ON t.buyer_nick = cum.buyer_nick
        LEFT JOIN tmp_r24 r24 ON t.buyer_nick = r24.buyer_nick
        LEFT JOIN tmp_l6m l6m ON t.buyer_nick = l6m.buyer_nick
        LEFT JOIN tmp_l1y l1y ON t.buyer_nick = l1y.buyer_nick
        LEFT JOIN tmp_discount disc ON t.buyer_nick = disc.buyer_nick
        LEFT JOIN (
            SELECT buyer_nick,
                MAX(CASE WHEN rank_num = 1 THEN category END) AS top_cat,
                MAX(CASE WHEN rank_num = 2 THEN category END) AS second_cat,
                MAX(CASE WHEN rank_num = 3 THEN category END) AS third_cat
            FROM tmp_cat GROUP BY buyer_nick
        ) cats ON t.buyer_nick = cats.buyer_nick
    )
    SELECT
        base.buyer_nick,
        v_snapshot_date AS snapshot_date,
        base.channel,
        base.client_monthly_tag,
        base.is_smoker,
        base.is_vic,
        base.buyer_type,
        base.vip_level,
        base.historical_gmv,
        base.historical_refund,
        base.historical_net_sales,
        base.total_orders,
        base.total_net_orders,
        base.refund_rate,
        base.rolling_24m_gmv,
        base.rolling_24m_netsales,
        base.rolling_24m_orders,
        base.rolling_24m_net_orders,
        base.l6m_netsales,
        base.l6m_gmv,
        base.l6m_orders,
        base.l6m_refund_rate,
        base.l1y_netsales,
        base.l1y_gmv,
        base.l1y_orders,
        base.l1y_refund_rate,
        base.avg_purchase_interval_days,
        base.discount_ratio,
        base.discount_sensitivity,
        base.first_purchase_date,
        base.last_purchase_date,
        base.city,
        base.top_cat,
        base.second_cat,
        base.third_cat,
        base.r_score,
        base.f_score,
        base.m_score,
        -- 13 类主表同款 segment
        CASE
            WHEN base.m_score >= 4 AND base.r_score >= 4 AND base.f_score >= 4 THEN '重要价值客户'
            WHEN base.m_score >= 4 AND base.r_score >= 4 AND base.f_score <= 3 THEN '重要发展客户'
            WHEN base.m_score >= 4 AND base.r_score <= 3 AND base.f_score >= 4 THEN '重要保持客户'
            WHEN base.m_score >= 4 AND base.r_score <= 3 AND base.f_score <= 3 THEN '重要挽留客户'
            WHEN base.m_score = 3 AND base.r_score >= 4 AND base.f_score >= 4 THEN '优质价值客户'
            WHEN base.m_score = 3 AND base.r_score >= 4 AND base.f_score <= 3 THEN '优质发展客户'
            WHEN base.m_score = 3 AND base.r_score <= 3 AND base.f_score >= 4 THEN '优质保持客户'
            WHEN base.m_score = 3 AND base.r_score <= 3 AND base.f_score <= 3 THEN '优质挽留客户'
            WHEN base.m_score = 2 AND base.r_score >= 4 THEN '潜力客户'
            WHEN base.m_score = 2 AND base.r_score <= 3 THEN '待激活客户'
            WHEN base.m_score = 1 AND base.r_score >= 4 THEN '新客户'
            WHEN base.m_score = 1 AND base.r_score IN (2, 3) THEN '低价值客户'
            WHEN base.r_score = 1 THEN '已流失'
            WHEN base.r_score = 0 THEN '无购买记录'
        END,
        -- churn_risk: R + F 组合 (不依赖 chat)
        CASE
            WHEN base.last_purchase_date IS NULL THEN '低'
            WHEN base.r_score = 1 THEN '高'
            WHEN base.r_score = 2 THEN '高'
            WHEN base.r_score = 3 AND base.f_score >= 4 THEN '中'
            WHEN base.r_score = 3 THEN '中'
            WHEN base.r_score = 4 AND base.f_score <= 2 THEN '中'
            ELSE '低'
        END
    FROM base
    ON DUPLICATE KEY UPDATE
        channel = VALUES(channel),
        client_monthly_tag = VALUES(client_monthly_tag),
        is_smoker = VALUES(is_smoker),
        is_vic = VALUES(is_vic),
        buyer_type = VALUES(buyer_type),
        vip_level = VALUES(vip_level),
        historical_gmv = VALUES(historical_gmv),
        historical_refund = VALUES(historical_refund),
        historical_net_sales = VALUES(historical_net_sales),
        total_orders = VALUES(total_orders),
        total_net_orders = VALUES(total_net_orders),
        refund_rate = VALUES(refund_rate),
        rolling_24m_gmv = VALUES(rolling_24m_gmv),
        rolling_24m_netsales = VALUES(rolling_24m_netsales),
        rolling_24m_orders = VALUES(rolling_24m_orders),
        rolling_24m_net_orders = VALUES(rolling_24m_net_orders),
        l6m_netsales = VALUES(l6m_netsales),
        l6m_gmv = VALUES(l6m_gmv),
        l6m_orders = VALUES(l6m_orders),
        l6m_refund_rate = VALUES(l6m_refund_rate),
        l1y_netsales = VALUES(l1y_netsales),
        l1y_gmv = VALUES(l1y_gmv),
        l1y_orders = VALUES(l1y_orders),
        l1y_refund_rate = VALUES(l1y_refund_rate),
        avg_purchase_interval_days = VALUES(avg_purchase_interval_days),
        discount_ratio = VALUES(discount_ratio),
        discount_sensitivity = VALUES(discount_sensitivity),
        first_purchase_date = VALUES(first_purchase_date),
        last_purchase_date = VALUES(last_purchase_date),
        city = VALUES(city),
        top_category = VALUES(top_category),
        second_category = VALUES(second_category),
        third_category = VALUES(third_category),
        rfm_recency_score = VALUES(rfm_recency_score),
        rfm_frequency_score = VALUES(rfm_frequency_score),
        rfm_monetary_score = VALUES(rfm_monetary_score),
        rfm_segment = VALUES(rfm_segment),
        churn_risk = VALUES(churn_risk);

    -- 清理临时表
    DROP TEMPORARY TABLE IF EXISTS tmp_target;
    DROP TEMPORARY TABLE IF EXISTS tmp_cum;
    DROP TEMPORARY TABLE IF EXISTS tmp_r24;
    DROP TEMPORARY TABLE IF EXISTS tmp_l6m;
    DROP TEMPORARY TABLE IF EXISTS tmp_l1y;
    DROP TEMPORARY TABLE IF EXISTS tmp_discount;
    DROP TEMPORARY TABLE IF EXISTS tmp_cat;

    -- 输出统计
    SELECT CONCAT('refresh_asof 完成: target_count=', v_target_count,
                  ', date=', v_snapshot_date,
                  ', 耗时=', TIMESTAMPDIFF(SECOND, v_start_time, CURRENT_TIMESTAMP), ' 秒') AS message;

    -- 验证: 该日期必须 > 0 行
    IF (SELECT COUNT(*) FROM target_buyers_precomputed_history WHERE snapshot_date = v_snapshot_date) = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'refresh_asof inserted 0 rows';
    END IF;
END$$

DELIMITER ;

-- ============================================
-- 手动测试 (单日)
-- ============================================
-- CALL refresh_target_buyers_asof('2025-04-01');
