-- ============================================
-- 目标买家订单明细预计算表创建和更新脚本
-- ============================================
-- 功能：
-- 1. 存储所有目标买家的订单明细(完整字段集)
-- 2. 每天下午14:08刷新近3个月数据
-- 3. 加快前端查询速度
-- ============================================

-- ============================================
-- 步骤1: 创建目标买家订单明细表
-- ============================================

DROP TABLE IF EXISTS target_buyer_orders;

CREATE TABLE target_buyer_orders (
    -- === 主键和基础信息 ===
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    订单号 VARCHAR(100) COMMENT '订单号',
    子订单号 VARCHAR(100) COMMENT '子订单号',
    买家昵称 MEDIUMTEXT COMMENT '买家昵称',

    -- === 渠道和客户信息 ===
    channel VARCHAR(3) NOT NULL COMMENT '渠道',
    店铺名称 MEDIUMTEXT COMMENT '店铺名称',
    买家openid MEDIUMTEXT COMMENT '买家openid',
    client_monthly_tag VARCHAR(20) COMMENT '新老客标识',

    -- === 时间信息 ===
    平台创建时间 DATETIME COMMENT '平台创建时间',
    付款时间 DATETIME COMMENT '付款时间',
    付款日期 DATE COMMENT '付款日期',
    最后付款时间 DATETIME COMMENT '最后付款时间',

    -- === 订单状态 ===
    子订单状态 MEDIUMTEXT COMMENT '子订单状态',
    是否聚划算 MEDIUMTEXT COMMENT '是否聚划算',
    预售单状态 MEDIUMTEXT COMMENT '预售单状态',

    -- === 商品信息 ===
    天猫ID VARCHAR(100) COMMENT '天猫ID',
    天猫商品编码 VARCHAR(100) COMMENT '天猫商品编码',
    天猫款号 MEDIUMTEXT COMMENT '天猫款号',
    天猫外部编码 VARCHAR(100) COMMENT '天猫外部编码',
    条形码 MEDIUMTEXT COMMENT '条形码',
    商品名称 MEDIUMTEXT COMMENT '商品名称',
    宝尊商品编码 MEDIUMTEXT COMMENT '宝尊商品编码',
    图片地址 MEDIUMTEXT COMMENT '商品图片地址',

    -- === 数量和价格 ===
    件数 INT COMMENT '件数',
    商品划线价 DOUBLE COMMENT '商品划线价',
    划线价总金额 DOUBLE COMMENT '划线价总金额',
    优惠金额 DOUBLE COMMENT '优惠金额',
    应付总金额 DOUBLE COMMENT '应付总金额',
    成交单价 DOUBLE COMMENT '成交单价',
    成交总金额 DOUBLE COMMENT '成交总金额',

    -- === 地理信息 ===
    省份 MEDIUMTEXT COMMENT '省份',
    城市 MEDIUMTEXT COMMENT '城市',

    -- === 退款信息 ===
    退款类型 MEDIUMTEXT COMMENT '退款类型：仅退款/退货退款',
    退款金额 DOUBLE COMMENT '退款金额',
    退款完结时间 DATETIME COMMENT '退款完结时间',
    退款完结日期 DATE COMMENT '退款完结日期',
    退款原因 MEDIUMTEXT COMMENT '退款原因',

    -- === 商品属性 ===
    商品sku属性 MEDIUMTEXT COMMENT '商品sku属性',
    skc TEXT COMMENT 'skc',
    product_name TEXT COMMENT 'product_name',
    rsp DOUBLE COMMENT 'rsp',

    -- === 分类信息 ===
    oms_category TEXT COMMENT 'oms_category',
    category TEXT COMMENT 'category',
    main_category TEXT COMMENT 'main_category',
    division TEXT COMMENT 'division',
    season_by_arrival TEXT COMMENT 'season_by_arrival',
    season_by_code TEXT COMMENT 'season_by_code',
    commercial_line TEXT COMMENT 'commercial_line',

    -- === 折扣信息 ===
    FP_MD VARCHAR(2) NOT NULL COMMENT 'FP/MD标识',

    -- === 分期信息 ===
    是否分期 TEXT COMMENT '是否分期',
    分期数 INT COMMENT '分期数',
    是否免息 TEXT COMMENT '是否免息',

    -- === 直播信息 ===
    livestream_flag INT NOT NULL DEFAULT 0 COMMENT '直播标识',
    直播场次ID VARCHAR(100) COMMENT '直播场次ID',
    直播场次标题 TEXT COMMENT '直播场次标题',
    直播开播时间 DATETIME COMMENT '直播开播时间',
    直播确认收货时间 DATETIME COMMENT '直播确认收货时间',
    直播确认收货金额 DOUBLE COMMENT '直播确认收货金额',

    -- === 其他标识 ===
    ff_flag INT NOT NULL DEFAULT 0 COMMENT 'ff_flag',
    sc_flag INT NOT NULL DEFAULT 0 COMMENT 'sc_flag',
    sc来源 TEXT COMMENT 'sc来源',
    sc推广日期 TEXT COMMENT 'sc推广日期',

    -- === 时间维度 ===
    pay_year TEXT COMMENT '支付年份',
    pay_season TEXT COMMENT '支付季节',
    pay_month INT COMMENT '支付月份',
    pay_week INT COMMENT '支付周数',

    -- === 索引 ===
    INDEX idx_订单号 (订单号),
    INDEX idx_买家昵称 (买家昵称(255)),
    INDEX idx_最后付款时间 (最后付款时间),
    INDEX idx_category (category(100)),
    INDEX idx_子订单号 (子订单号),
    INDEX idx_channel (channel),
    INDEX idx_client_monthly_tag (client_monthly_tag)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='目标买家订单明细预计算表 - 每天下午14:08刷新近3个月';

-- ============================================
-- 步骤2: 初始加载历史数据(一次性执行)
-- ============================================

INSERT INTO target_buyer_orders (
    channel, 店铺名称, 订单号, 子订单号, 买家昵称, 买家openid, client_monthly_tag,
    平台创建时间, 付款时间, 付款日期, 最后付款时间, 子订单状态, 图片地址,
    是否聚划算, 预售单状态, 天猫ID, 天猫商品编码, 天猫款号, 天猫外部编码,
    条形码, 商品名称, 宝尊商品编码, 件数, 商品划线价, 划线价总金额,
    优惠金额, 应付总金额, 成交单价, 成交总金额, 省份, 城市,
    退款类型, 退款金额, 退款完结时间, 退款完结日期, 退款原因,
    商品sku属性, skc, product_name, rsp, oms_category, category,
    main_category, division, season_by_arrival, season_by_code,
    commercial_line, FP_MD, 是否分期, 分期数, 是否免息,
    livestream_flag, 直播场次ID, 直播场次标题, 直播开播时间,
    直播确认收货时间, 直播确认收货金额, ff_flag, sc_flag,
    sc来源, sc推广日期, pay_year, pay_season, pay_month, pay_week
)
SELECT
    channel, 店铺名称, 订单号, 子订单号, 买家昵称, 买家openid, client_monthly_tag,
    平台创建时间, 付款时间, 付款日期, 最后付款时间, 子订单状态, 图片地址,
    是否聚划算, 预售单状态, 天猫ID, 天猫商品编码, 天猫款号, 天猫外部编码,
    条形码, 商品名称, 宝尊商品编码, 件数, 商品划线价, 划线价总金额,
    优惠金额, 应付总金额, 成交单价, 成交总金额, 省份, 城市,
    退款类型, 退款金额, 退款完结时间, 退款完结日期, 退款原因,
    商品sku属性, skc, product_name, rsp, oms_category, category,
    main_category, division, season_by_arrival, season_by_code,
    commercial_line, FP_MD, 是否分期, 分期数, 是否免息,
    livestream_flag, 直播场次ID, 直播场次标题, 直播开播时间,
    直播确认收货时间, 直播确认收货金额, ff_flag, sc_flag,
    sc来源, sc推广日期, pay_year, pay_season, pay_month, pay_week
FROM dunhill_t01_trade_line
WHERE 买家昵称 IN (SELECT buyer_nick FROM target_buyers_precomputed)
  AND 买家昵称 IS NOT NULL
  AND 买家昵称 != '';

-- ============================================
-- 步骤3: 创建定时更新存储过程
-- ============================================

DROP PROCEDURE IF EXISTS refresh_target_buyer_orders;

DELIMITER $$

CREATE PROCEDURE refresh_target_buyer_orders()
BEGIN
    DECLARE start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    DECLARE deleted_rows INT DEFAULT 0;
    DECLARE inserted_rows INT DEFAULT 0;

    -- 记录开始
    SELECT CONCAT('🚀 开始刷新目标买家订单明细表: ', start_time) AS message;

    -- 3.1 删除近3个月的数据
    DELETE FROM target_buyer_orders
    WHERE 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 3 MONTH);

    SET deleted_rows = ROW_COUNT();
    SELECT CONCAT('🗑️  删除了 ', deleted_rows, ' 条近3个月的订单记录') AS message;

    -- 3.2 重新插入近3个月的数据
    INSERT INTO target_buyer_orders (
        channel, 店铺名称, 订单号, 子订单号, 买家昵称, 买家openid, client_monthly_tag,
        平台创建时间, 付款时间, 付款日期, 最后付款时间, 子订单状态, 图片地址,
        是否聚划算, 预售单状态, 天猫ID, 天猫商品编码, 天猫款号, 天猫外部编码,
        条形码, 商品名称, 宝尊商品编码, 件数, 商品划线价, 划线价总金额,
        优惠金额, 应付总金额, 成交单价, 成交总金额, 省份, 城市,
        退款类型, 退款金额, 退款完结时间, 退款完结日期, 退款原因,
        商品sku属性, skc, product_name, rsp, oms_category, category,
        main_category, division, season_by_arrival, season_by_code,
        commercial_line, FP_MD, 是否分期, 分期数, 是否免息,
        livestream_flag, 直播场次ID, 直播场次标题, 直播开播时间,
        直播确认收货时间, 直播确认收货金额, ff_flag, sc_flag,
        sc来源, sc推广日期, pay_year, pay_season, pay_month, pay_week
    )
    SELECT
        channel, 店铺名称, 订单号, 子订单号, 买家昵称, 买家openid, client_monthly_tag,
        平台创建时间, 付款时间, 付款日期, 最后付款时间, 子订单状态, 图片地址,
        是否聚划算, 预售单状态, 天猫ID, 天猫商品编码, 天猫款号, 天猫外部编码,
        条形码, 商品名称, 宝尊商品编码, 件数, 商品划线价, 划线价总金额,
        优惠金额, 应付总金额, 成交单价, 成交总金额, 省份, 城市,
        退款类型, 退款金额, 退款完结时间, 退款完结日期, 退款原因,
        商品sku属性, skc, product_name, rsp, oms_category, category,
        main_category, division, season_by_arrival, season_by_code,
        commercial_line, FP_MD, 是否分期, 分期数, 是否免息,
        livestream_flag, 直播场次ID, 直播场次标题, 直播开播时间,
        直播确认收货时间, 直播确认收货金额, ff_flag, sc_flag,
        sc来源, sc推广日期, pay_year, pay_season, pay_month, pay_week
    FROM dunhill_t01_trade_line
    WHERE 买家昵称 IN (SELECT buyer_nick FROM target_buyers_precomputed)
      AND 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 3 MONTH)
      AND 买家昵称 IS NOT NULL
      AND 买家昵称 != '';

    SET inserted_rows = ROW_COUNT();
    SELECT CONCAT('➕ 插入了 ', inserted_rows, ' 条近3个月的订单记录') AS message;

    -- 输出统计信息
    SELECT CONCAT('✅ 刷新完成！') AS message;
    SELECT CONCAT('📊 当前表中订单总数: ', (SELECT COUNT(*) FROM target_buyer_orders)) AS total_orders;
    SELECT CONCAT('⏱️  总耗时: ', TIMESTAMPDIFF(SECOND, start_time, CURRENT_TIMESTAMP), ' 秒') AS duration;
    SELECT CONCAT('🕒 最后更新时间: ', CURRENT_TIMESTAMP) AS last_updated;

    -- 按月份统计
    SELECT
        DATE_FORMAT(最后付款时间, '%Y-%m') as month,
        COUNT(*) as order_count,
        SUM(成交总金额) as total_gmv
    FROM target_buyer_orders
    WHERE 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
    GROUP BY DATE_FORMAT(最后付款时间, '%Y-%m')
    ORDER BY month DESC;

END$$

DELIMITER ;

-- ============================================
-- 步骤4: 创建定时事件(每天下午14:08执行)
-- ============================================

-- 启用事件调度器 (需要SUPER权限, 如果已启用可跳过)
-- SET GLOBAL event_scheduler = ON;

-- 删除旧事件(如果存在)
DROP EVENT IF EXISTS event_refresh_target_buyer_orders;

-- 创建新事件
CREATE EVENT event_refresh_target_buyer_orders
ON SCHEDULE EVERY 1 DAY
STARTS CONCAT(CURDATE() + INTERVAL 1 DAY, ' 14:08:00')
COMMENT '每天下午14:08刷新目标买家订单明细表(近3个月)'
DO
CALL refresh_target_buyer_orders();

-- ============================================
-- 步骤5: 查询示例
-- ============================================

-- 1. 手动触发更新(测试用)
-- CALL refresh_target_buyer_orders();

-- 2. 查看所有订单
-- SELECT * FROM target_buyer_orders ORDER BY 最后付款时间 DESC LIMIT 100;

-- 3. 查询特定买家的订单
-- SELECT * FROM target_buyer_orders WHERE 买家昵称 = 'xxx' ORDER BY 最后付款时间 DESC;

-- 4. 查询近1年的订单
-- SELECT * FROM target_buyer_orders WHERE 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 1 YEAR);

-- 5. 按品类统计
-- SELECT category, COUNT(*) as count, SUM(成交总金额) as gmv FROM target_buyer_orders GROUP BY category;

-- ============================================
-- 验证和监控
-- ============================================

-- 查看事件调度器状态
-- SHOW VARIABLES LIKE 'event_scheduler';

-- 查看所有事件
-- SHOW EVENTS;

-- 查看下一次执行时间
-- SELECT * FROM information_schema.EVENTS WHERE EVENT_NAME = 'event_refresh_target_buyer_orders';
