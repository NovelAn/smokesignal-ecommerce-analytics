-- ============================================
-- 场外信息记录表 (External Records)
-- 用于存储客户的线下消费和私域沟通记录
-- ============================================

CREATE TABLE IF NOT EXISTS external_records (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_nick VARCHAR(100) NOT NULL COMMENT '客户昵称（关联线上客户）',
  record_type ENUM('communication', 'purchase') NOT NULL COMMENT '类型：沟通/消费',

  -- 通用字段
  record_date DATE NOT NULL COMMENT '起始日期',
  date_to DATE COMMENT '结束日期（为空表示单日记录）',
  channel VARCHAR(100) COMMENT '渠道：微信/电话/门店名称',
  content TEXT COMMENT '内容描述',
  notes TEXT COMMENT '备注',

  -- 消费类型专用
  amount DECIMAL(10, 2) COMMENT '消费金额（仅消费类型）',
  category VARCHAR(200) COMMENT '商品品类（仅消费类型，多选逗号分隔）',
  attachment_url VARCHAR(500) COMMENT '附件图片路径',

  -- 元数据
  created_by VARCHAR(50) COMMENT '录入人',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  INDEX idx_user_nick (user_nick),
  INDEX idx_record_type (record_type),
  INDEX idx_record_date (record_date),
  INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='场外信息记录表';

-- ============================================
-- 示例数据（可选，用于测试）
-- ============================================

-- INSERT INTO external_records (user_nick, record_type, record_date, channel, content, notes, amount, category, created_by) VALUES
-- ('王小明', 'communication', '2026-02-20', '微信', '咨询新品烟斗的到货时间', '客户对新出的限量版很感兴趣', NULL, NULL, 'admin'),
-- ('李女士', 'purchase', '2026-02-18', '北京SKP', '购买限量版打火机', 'VIP客户，赠送了会员礼品', 8500.00, 'Lighters', 'admin'),
-- ('张先生', 'communication', '2026-02-15', '电话', '投诉物流延迟问题', '已跟进处理，客户满意', NULL, NULL, 'admin');
