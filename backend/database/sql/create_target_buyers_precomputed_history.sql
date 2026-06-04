-- ============================================
-- target_buyers_precomputed_history 表创建
-- ============================================
-- 用途：每日 snapshot target_buyers_precomputed 的真 ASOF 状态
-- 刷新：每天上午 11:30 snapshot_target_buyers_history() 写入
-- 保留：24 个月（按月 RANGE PARTITION）
-- 数据源：dunhill_t01_trade_line + 主表 target_buyers_precomputed
-- v2 API 路径保持不变
-- ============================================

DROP TABLE IF EXISTS target_buyers_precomputed_history;

CREATE TABLE target_buyers_precomputed_history (
    -- === 标识 ===
    buyer_nick VARCHAR(255) NOT NULL COMMENT '买家昵称',
    snapshot_date DATE NOT NULL COMMENT 'snapshot 日期 (ASOF 基准日)',

    -- === 渠道/新老客 ===
    channel VARCHAR(10) COMMENT '渠道: DTC/PFS',
    client_monthly_tag VARCHAR(50) COMMENT '新老客标识',

    -- === 买家类型标签 (基于 ASOF d 判定) ===
    is_smoker BOOLEAN DEFAULT FALSE COMMENT 'd 之前买过 Pipes/Lighters',
    is_vic BOOLEAN DEFAULT FALSE COMMENT 'd 往前 24M 净销售 >= 30K',
    buyer_type VARCHAR(50) COMMENT 'SMOKER/VIC/BOTH',
    vip_level VARCHAR(10) COMMENT 'V3/V2/V1/V0/Non-VIP',

    -- === 累计指标 (< d 全部交易) ===
    historical_gmv DECIMAL(18, 2) COMMENT '历史 GMV',
    historical_refund DECIMAL(18, 2) COMMENT '历史退款',
    historical_net_sales DECIMAL(18, 2) COMMENT '历史净销售',
    total_orders INT COMMENT '历史订单数',
    total_net_orders INT COMMENT '历史有效订单数',
    refund_rate DECIMAL(5, 4) COMMENT '退款率',

    -- === Rolling 24M ([d-24M, d)) ===
    rolling_24m_gmv DECIMAL(18, 2),
    rolling_24m_netsales DECIMAL(18, 2),
    rolling_24m_orders INT,
    rolling_24m_net_orders INT,

    -- === L6M ([d-6M, d)) ===
    l6m_gmv DECIMAL(18, 2),
    l6m_netsales DECIMAL(18, 2),
    l6m_orders INT,
    l6m_refund_rate DECIMAL(5, 4),

    -- === L1Y ([d-12M, d)) ===
    l1y_gmv DECIMAL(18, 2),
    l1y_netsales DECIMAL(18, 2),
    l1y_orders INT,
    l1y_refund_rate DECIMAL(5, 4),

    -- === 频率 ===
    avg_purchase_interval_days DECIMAL(10, 2),

    -- === 折扣敏感度 ===
    discount_ratio DECIMAL(5, 2),
    discount_sensitivity VARCHAR(20) COMMENT '高度敏感/中度敏感/低度敏感',

    -- === 时间边界 ===
    first_purchase_date DATETIME,
    last_purchase_date DATETIME,

    -- === 城市 ===
    city VARCHAR(100),

    -- === 品类偏好 (TOP3) ===
    top_category VARCHAR(50),
    second_category VARCHAR(50),
    third_category VARCHAR(50),

    -- === RFM (主表 procedure 同款阈值, ASOF 基于 d) ===
    rfm_recency_score INT DEFAULT 0,
    rfm_frequency_score INT DEFAULT 0,
    rfm_monetary_score INT DEFAULT 0,
    rfm_segment VARCHAR(50) COMMENT '主表 13 类同款',

    -- === 流失风险 (R+F 组合, 不依赖 chat) ===
    churn_risk VARCHAR(20) COMMENT '高/中/低',

    -- === 主键 + 索引 ===
    PRIMARY KEY (buyer_nick, snapshot_date),
    INDEX idx_snapshot_buyer_type (snapshot_date, buyer_type),
    INDEX idx_snapshot_vip (snapshot_date, vip_level),
    INDEX idx_snapshot_date (snapshot_date),
    INDEX idx_buyer_date (buyer_nick, snapshot_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='目标买家历史快照 - 每天 11:30 snapshot, 保留 24M'
PARTITION BY RANGE (TO_DAYS(snapshot_date)) (
    PARTITION p202504 VALUES LESS THAN (TO_DAYS('2025-05-01')),
    PARTITION p202505 VALUES LESS THAN (TO_DAYS('2025-06-01')),
    PARTITION p202506 VALUES LESS THAN (TO_DAYS('2025-07-01')),
    PARTITION p202507 VALUES LESS THAN (TO_DAYS('2025-08-01')),
    PARTITION p202508 VALUES LESS THAN (TO_DAYS('2025-09-01')),
    PARTITION p202509 VALUES LESS THAN (TO_DAYS('2025-10-01')),
    PARTITION p202510 VALUES LESS THAN (TO_DAYS('2025-11-01')),
    PARTITION p202511 VALUES LESS THAN (TO_DAYS('2025-12-01')),
    PARTITION p202512 VALUES LESS THAN (TO_DAYS('2026-01-01')),
    PARTITION p202601 VALUES LESS THAN (TO_DAYS('2026-02-01')),
    PARTITION p202602 VALUES LESS THAN (TO_DAYS('2026-03-01')),
    PARTITION p202603 VALUES LESS THAN (TO_DAYS('2026-04-01')),
    PARTITION p202604 VALUES LESS THAN (TO_DAYS('2026-05-01')),
    PARTITION p202605 VALUES LESS THAN (TO_DAYS('2026-06-01')),
    PARTITION p202606 VALUES LESS THAN (TO_DAYS('2026-07-01')),
    PARTITION p202607 VALUES LESS THAN (TO_DAYS('2026-08-01')),
    PARTITION p202608 VALUES LESS THAN (TO_DAYS('2026-09-01')),
    PARTITION p202609 VALUES LESS THAN (TO_DAYS('2026-10-01')),
    PARTITION p202610 VALUES LESS THAN (TO_DAYS('2026-11-01')),
    PARTITION p202611 VALUES LESS THAN (TO_DAYS('2026-12-01')),
    PARTITION p202612 VALUES LESS THAN (TO_DAYS('2027-01-01')),
    PARTITION p202701 VALUES LESS THAN (TO_DAYS('2027-02-01')),
    PARTITION p202702 VALUES LESS THAN (TO_DAYS('2027-03-01')),
    PARTITION p202703 VALUES LESS THAN (TO_DAYS('2027-04-01')),
    PARTITION p202704 VALUES LESS THAN (TO_DAYS('2027-05-01')),
    PARTITION p202705 VALUES LESS THAN (TO_DAYS('2027-06-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- ============================================
-- 验证 DDL
-- ============================================

-- 1. 表结构
SELECT 'Table created' AS status;

-- 2. 分区列表
SELECT
    PARTITION_NAME,
    PARTITION_DESCRIPTION,
    TABLE_ROWS
FROM information_schema.PARTITIONS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'target_buyers_precomputed_history'
ORDER BY PARTITION_ORDINAL_POSITION;

-- 3. 索引列表
SELECT
    INDEX_NAME,
    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS columns
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'target_buyers_precomputed_history'
GROUP BY INDEX_NAME;
