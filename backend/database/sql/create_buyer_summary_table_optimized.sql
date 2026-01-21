-- ============================================
-- 完整优化方案：买家汇总表 + 基础表索引
-- ============================================

-- ============================================
-- 步骤1: 在基础表上创建索引（加快视图查询）
-- ============================================

-- 在 dunhill_bi订单源 表上创建索引
CREATE INDEX IF NOT EXISTS idx_bi_buyer_nick ON dunhill_bi订单源(买家昵称);
CREATE INDEX IF NOT EXISTS idx_bi_payment_time ON dunhill_bi订单源(付款时间);
CREATE INDEX IF NOT EXISTS idx_bi_order_id ON dunhill_bi订单源(订单号);
CREATE INDEX IF NOT EXISTS idx_bi_nick_time ON dunhill_bi订单源(买家昵称, 付款时间);

-- 在 dunhill_dtc订单源_hive 表上创建索引
CREATE INDEX IF NOT EXISTS idx_dtc_buyer_nick ON dunhill_dtc订单源_hive(买家昵称);
CREATE INDEX IF NOT EXISTS idx_dtc_payment_time ON dunhill_dtc订单源_hive(付款时间);
CREATE INDEX IF NOT EXISTS idx_dtc_order_id ON dunhill_dtc订单源_hive(订单号);
CREATE INDEX IF NOT EXISTS idx_dtc_nick_time ON dunhill_dtc订单源_hive(买家昵称, 付款时间);

-- 在退款表上创建索引（加快JOIN）
CREATE INDEX IF NOT EXISTS idx_tm_refund_order ON dunhill_tm退款源(订单编号, 商品编码);
CREATE INDEX IF NOT EXISTS idx_dtc_refund_order ON dunhill_dtc退款源_hive(订单号, 子订单号);

-- ============================================
-- 步骤2: 创建买家汇总表
-- ============================================

CREATE TABLE IF NOT EXISTS buyer_summary (
    buyer_nick VARCHAR(255) PRIMARY KEY,
    first_order_date DATETIME,
    last_order_date DATETIME,
    total_orders INT,
    total_gmv DECIMAL(18, 2),
    total_refund DECIMAL(18, 2),
    city VARCHAR(100),
    last_client_monthly_tag VARCHAR(50),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_last_order (last_order_date),
    INDEX idx_city (city)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='买家汇总表，每天凌晨2点自动更新';

-- ============================================
-- 步骤3: 初始化数据
-- ============================================

-- 清空旧数据（如果表已存在）
TRUNCATE TABLE buyer_summary;

-- 从视图导入初始数据
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
    SUM(IFNULL(退款金额, 0)) as total_refund,
    MAX(城市) as city,
    MAX(client_monthly_tag) as last_client_monthly_tag
FROM dunhill_t01_trade_line
WHERE 买家昵称 IS NOT NULL AND 买家昵称 != ''
GROUP BY 买家昵称;

-- ============================================
-- 步骤4: 创建存储过程
-- ============================================

DELIMITER $$

DROP PROCEDURE IF EXISTS refresh_buyer_summary$$

CREATE PROCEDURE refresh_buyer_summary()
BEGIN
    DECLARE start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    DECLARE affected_rows INT DEFAULT 0;

    -- 记录开始
    SELECT CONCAT('开始刷新买家汇总表: ', start_time) AS message;

    -- 更新现有买家数据
    UPDATE buyer_summary bs
    INNER JOIN (
        SELECT
            买家昵称,
            MIN(最后付款时间) as first_order_date,
            MAX(最后付款时间) as last_order_date,
            COUNT(DISTINCT 订单号) as total_orders,
            SUM(成交总金额) as total_gmv,
            SUM(IFNULL(退款金额, 0)) as total_refund,
            MAX(城市) as city,
            MAX(client_monthly_tag) as last_client_monthly_tag
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 IS NOT NULL AND 买家昵称 != ''
        GROUP BY 买家昵称
    ) new_data ON bs.buyer_nick = new_data.买家昵称
    SET
        bs.first_order_date = new_data.first_order_date,
        bs.last_order_date = new_data.last_order_date,
        bs.total_orders = new_data.total_orders,
        bs.total_gmv = new_data.total_gmv,
        bs.total_refund = new_data.total_refund,
        bs.city = new_data.city,
        bs.last_client_monthly_tag = new_data.last_client_monthly_tag,
        bs.updated_at = CURRENT_TIMESTAMP;

    SET affected_rows = ROW_COUNT();

    -- 插入新买家
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
        买家昵称,
        MIN(最后付款时间),
        MAX(最后付款时间),
        COUNT(DISTINCT 订单号),
        SUM(成交总金额),
        SUM(IFNULL(退款金额, 0)),
        MAX(城市),
        MAX(client_monthly_tag)
    FROM dunhill_t01_trade_line
    WHERE 买家昵称 IS NOT NULL
      AND 买家昵称 != ''
      AND 买家昵称 NOT IN (SELECT buyer_nick FROM buyer_summary)
    GROUP BY 买家昵称;

    SET affected_rows = affected_rows + ROW_COUNT();

    -- 输出结果
    SELECT CONCAT('✅ 刷新完成！更新/插入了 ', affected_rows, ' 条记录') AS message;
    SELECT CONCAT('耗时: ', TIMESTAMPDIFF(SECOND, start_time, CURRENT_TIMESTAMP), ' 秒') AS duration;
    SELECT CONCAT('当前买家总数: ', (SELECT COUNT(*) FROM buyer_summary)) AS total_buyers;

END$$

DELIMITER ;

-- ============================================
-- 步骤5: 创建定时任务（每天凌晨2点）
-- ============================================

-- 启用事件调度器
SET GLOBAL event_scheduler = ON;

-- 删除旧事件（如果存在）
DROP EVENT IF EXISTS event_refresh_buyer_summary;

-- 创建新事件
CREATE EVENT event_refresh_buyer_summary
ON SCHEDULE EVERY 1 DAY
STARTS CONCAT(CURDATE() + INTERVAL 1 DAY, ' 02:00:00')
COMMENT '每天凌晨2点刷新买家汇总表'
DO
CALL refresh_buyer_summary();

-- ============================================
-- 步骤6: 创建辅助视图（方便查询）
-- ============================================

CREATE OR REPLACE VIEW v_buyer_list AS
SELECT
    buyer_nick,
    first_order_date,
    last_order_date,
    total_orders,
    total_gmv,
    total_refund,
    (total_gmv - total_refund) as net_sales,
    city,
    last_client_monthly_tag,
    updated_at
FROM buyer_summary
ORDER BY last_order_date DESC;

-- ============================================
-- 使用示例
-- ============================================

-- 1. 手动刷新汇总表
-- CALL refresh_buyer_summary();

-- 2. 获取所有买家（超快！）
-- SELECT buyer_nick FROM buyer_summary ORDER BY last_order_date DESC LIMIT 100;

-- 3. 搜索买家
-- SELECT buyer_nick FROM buyer_summary WHERE buyer_nick LIKE '%张%' LIMIT 100;

-- 4. 按日期范围筛选
-- SELECT buyer_nick FROM buyer_summary
-- WHERE last_order_date >= '2024-01-01'
-- ORDER BY last_order_date DESC
-- LIMIT 100;

-- 5. 统计信息
-- SELECT
--     COUNT(*) as total_buyers,
--     SUM(total_gmv) as total_gmv,
--     MAX(updated_at) as last_updated
-- FROM buyer_summary;

-- 6. 查看最近更新的买家
-- SELECT buyer_nick, updated_at
-- FROM buyer_summary
-- ORDER BY updated_at DESC
-- LIMIT 10;

-- ============================================
-- 监控和维护
-- ============================================

-- 查看事件调度器状态
-- SHOW VARIABLES LIKE 'event_scheduler';

-- 查看所有事件
-- SHOW EVENTS;

-- 查看下一次执行时间
-- SELECT * FROM information_schema.EVENTS
-- WHERE EVENT_NAME = 'event_refresh_buyer_summary';

-- 手动触发一次测试
-- CALL refresh_buyer_summary();
