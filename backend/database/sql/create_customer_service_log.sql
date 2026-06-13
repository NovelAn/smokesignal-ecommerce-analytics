-- ============================================
-- customer_service_log 表
-- ============================================
-- 用途：客服操作记录，独立于 target_buyers_precomputed
-- 关联：LEFT JOIN target_buyers_precomputed.buyer_nick
-- 用法：POST /api/v2/service/mark → UPSERT
-- Round 1: 先做 status + notes, Round 2 扩展
-- ============================================

DROP TABLE IF EXISTS customer_service_log;

CREATE TABLE customer_service_log (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    buyer_nick  VARCHAR(255) NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'pending'
                COMMENT 'pending / contacted / resolved',
    notes       TEXT COMMENT '客服备注',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_buyer (buyer_nick),
    INDEX idx_status (status),
    INDEX idx_updated (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='客服操作记录 (Round 1 CRM 增强)';
