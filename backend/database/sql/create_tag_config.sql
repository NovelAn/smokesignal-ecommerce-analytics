-- ============================================
-- 标签阈值配置表 (P2: Tag Configurability)
-- ============================================
-- 用途: 将硬编码在 stored procedure 和 tag_calculator.py 中的阈值
--       抽到数据库表, 让前端可读可写, 不用重新部署 SQL
--
-- 影响范围:
--   1. create_target_buyers_precomputed.sql 中的 stored procedure 改造
--      在 procedure 顶部用 SELECT INTO 读这些值, CASE 内全部用变量
--   2. backend/analytics/tag_calculator.py 的 calculate_* 方法
--      加 config 参数, 从 TagConfigManager 缓存读
--
-- Seed 值完全复刻现有硬编码, 跑完 stored procedure 后字段值应保持不变
-- ============================================

CREATE TABLE IF NOT EXISTS tag_config (
  config_key VARCHAR(64) PRIMARY KEY,
  config_value DECIMAL(18,4) NOT NULL,
  config_label VARCHAR(128) NOT NULL,
  category ENUM('vip', 'churn', 'discount', 'lifecycle', 'purchase_freq', 'chat_recent', 'smoker') NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  updated_by VARCHAR(64) DEFAULT 'system',
  INDEX idx_category (category, sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='标签阈值配置 (P2)';

-- ============================================
-- Seed: 17 条记录, 复刻现有硬编码
-- ============================================
INSERT INTO tag_config (config_key, config_value, config_label, category, sort_order) VALUES
  -- VIP 等级 (4 条)
  ('vip_v0_min',  30000,  'VIP V0 起点 (Rolling 24M 净销售)',     'vip', 1),
  ('vip_v1_min',  50000,  'VIP V1 起点',                         'vip', 2),
  ('vip_v2_min',  150000, 'VIP V2 起点',                         'vip', 3),
  ('vip_v3_min',  450000, 'VIP V3 起点',                         'vip', 4),
  -- 流失风险 (2 条)
  ('churn_high_days_since_chat',  180, '流失=高: 距上次聊天超过(天)',   'churn', 1),
  ('churn_medium_days_since_chat', 90, '流失=中: 距上次聊天超过(天)',    'churn', 2),
  -- 折扣敏感度 (2 条)
  ('discount_high_ratio',  0.7, '折扣敏感=高: 折扣订单占比下限',     'discount', 1),
  ('discount_medium_ratio', 0.4, '折扣敏感=中: 折扣订单占比下限',    'discount', 2),
  -- 生命周期 (3 条)
  ('lifecycle_new_customer_days',    90,  '新客: 距首次购买不超过(天)',  'lifecycle', 1),
  ('lifecycle_mature_min_netsales',  50000, '成熟客户: Rolling 24M 起点', 'lifecycle', 2),
  ('lifecycle_churn_days_since_purchase', 365, '流失: 距上次购买超过(天)', 'lifecycle', 3),
  -- 购买频次 (3 条)
  ('purchase_freq_high',  6, '高频: 年订单数下限',                'purchase_freq', 1),
  ('purchase_freq_medium', 3, '中频: 年订单数下限',                'purchase_freq', 2),
  ('purchase_freq_low',    1, '低频: 年订单数下限',                'purchase_freq', 3),
  -- 近期聊天活跃度 (3 条)
  ('chat_recent_very_active', 20, '近期聊天=非常活跃: 近30天消息数下限',  'chat_recent', 1),
  ('chat_recent_active',       5, '近期聊天=活跃',                    'chat_recent', 2),
  ('chat_recent_normal',       1, '近期聊天=一般',                    'chat_recent', 3)
ON DUPLICATE KEY UPDATE
  config_value = VALUES(config_value),
  config_label = VALUES(config_label);