-- 方案2：视图修复前的临时方案
-- 手动 LEFT JOIN 退款表计算退款金额

DROP PROCEDURE IF EXISTS refresh_buyer_summary;

DELIMITER $$

CREATE PROCEDURE refresh_buyer_summary()
BEGIN
    DECLARE start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    DECLARE affected_rows INT DEFAULT 0;

    SELECT CONCAT('开始刷新买家汇总表: ', start_time) AS message;

    -- 先清空汇总表
    TRUNCATE TABLE buyer_summary;

    -- 1. 先从 bi 订单源导入（并关联 TM 退款表）
    INSERT INTO buyer_summary (
        buyer_nick, first_order_date, last_order_date, total_orders,
        total_gmv, total_refund, city, last_client_monthly_tag
    )
    SELECT
        bi.买家昵称 as buyer_nick,
        MIN(bi.付款时间) as first_order_date,
        MAX(bi.付款时间) as last_order_date,
        COUNT(DISTINCT bi.订单号) as total_orders,
        SUM(bi.成交总金额) as total_gmv,
        COALESCE(SUM(rfd.买家退款金额), 0) as total_refund,  -- ← 从退款表获取
        MAX(bi.城市) as city,
        MAX(bi.client_monthly_tag) as last_client_monthly_tag
    FROM dunhill_bi订单源 bi
    LEFT JOIN dunhill_tm退款源 rfd
        ON bi.订单号 = rfd.订单编号
        AND bi.天猫商品编码 = rfd.商品编码
    WHERE bi.买家昵称 IS NOT NULL
      AND bi.买家昵称 != ''
      AND bi.付款时间 IS NOT NULL
    GROUP BY bi.买家昵称;

    SET affected_rows = ROW_COUNT();

    -- 2. 从 dtc 订单源导入（并关联 DTC 退款表）
    INSERT IGNORE INTO buyer_summary (
        buyer_nick, first_order_date, last_order_date, total_orders,
        total_gmv, total_refund, city, last_client_monthly_tag
    )
    SELECT
        dtc.买家昵称 as buyer_nick,
        MIN(dtc.付款时间) as first_order_date,
        MAX(dtc.付款时间) as last_order_date,
        COUNT(DISTINCT dtc.订单号) as total_orders,
        SUM(dtc.成交总金额) as total_gmv,
        COALESCE(SUM(d_rfd.退款金额), 0) as total_refund,  -- ← 从退款表获取
        MAX(dtc.城市) as city,
        MAX(dtc.client_monthly_tag) as last_client_monthly_tag
    FROM dunhill_dtc订单源_hive dtc
    LEFT JOIN dunhill_dtc退款源_hive d_rfd
        ON dtc.订单号 = d_rfd.订单号
        AND dtc.子订单号 = d_rfd.子订单号
    WHERE dtc.买家昵称 IS NOT NULL
      AND dtc.买家昵称 != ''
      AND dtc.付款时间 IS NOT NULL
    GROUP BY dtc.买家昵称;

    SET affected_rows = affected_rows + ROW_COUNT();

    -- 输出结果
    SELECT CONCAT('✅ 刷新完成！更新了 ', affected_rows, ' 条记录') AS message;
    SELECT CONCAT('耗时: ', TIMESTAMPDIFF(SECOND, start_time, CURRENT_TIMESTAMP), ' 秒') AS duration;
    SELECT CONCAT('当前买家总数: ', (SELECT COUNT(*) FROM buyer_summary)) AS total_buyers;
    SELECT CONCAT('有退款记录的买家: ', (SELECT COUNT(*) FROM buyer_summary WHERE total_refund > 0)) AS refund_buyers;

END$$

DELIMITER ;

-- 手动刷新测试
CALL refresh_buyer_summary();
