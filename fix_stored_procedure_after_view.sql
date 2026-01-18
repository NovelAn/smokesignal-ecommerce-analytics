-- 视图修复后，使用这个版本更新存储过程
-- 包含正确的退款数据计算

DROP PROCEDURE IF EXISTS refresh_buyer_summary;

DELIMITER $$

CREATE PROCEDURE refresh_buyer_summary()
BEGIN
    DECLARE start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    DECLARE affected_rows INT DEFAULT 0;

    SELECT CONCAT('开始刷新买家汇总表: ', start_time) AS message;

    -- 先清空汇总表
    TRUNCATE TABLE buyer_summary;

    -- 从修复后的视图导入数据（包含退款信息）
    INSERT INTO buyer_summary (
        buyer_nick,
        first_order_date,
        last_order_date,
        total_orders,
        total_gmv,
        total_refund,
        city,
        last_client_monthly_tag
    )
    SELECT
        买家昵称 as buyer_nick,
        MIN(最后付款时间) as first_order_date,
        MAX(最后付款时间) as last_order_date,
        COUNT(DISTINCT 订单号) as total_orders,
        SUM(成交总金额) as total_gmv,
        SUM(IFNULL(退款金额, 0)) as total_refund,  -- ← 从视图获取真实退款数据
        MAX(城市) as city,
        MAX(client_monthly_tag) as last_client_monthly_tag
    FROM dunhill_t01_trade_line
    WHERE 买家昵称 IS NOT NULL
      AND 买家昵称 != ''
      AND 最后付款时间 IS NOT NULL
      AND 最后付款时间 REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
    GROUP BY 买家昵称;

    SET affected_rows = ROW_COUNT();

    -- 输出结果
    SELECT CONCAT('✅ 刷新完成！更新了 ', affected_rows, ' 条记录') AS message;
    SELECT CONCAT('耗时: ', TIMESTAMPDIFF(SECOND, start_time, CURRENT_TIMESTAMP), ' 秒') AS duration;
    SELECT CONCAT('当前买家总数: ', (SELECT COUNT(*) FROM buyer_summary)) AS total_buyers;

END$$

DELIMITER ;

-- 手动刷新测试
CALL refresh_buyer_summary();

-- 验证退款数据
SELECT
    buyer_nick,
    total_gmv,
    total_refund,
    (total_gmv - total_refund) as net_sales
FROM buyer_summary
WHERE total_refund > 0
LIMIT 10;
