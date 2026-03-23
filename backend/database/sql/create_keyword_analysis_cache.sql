-- 关键词分析缓存表
-- 用于存储预计算的关键词分析结果

CREATE TABLE IF NOT EXISTS keyword_analysis_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    buyer_type ENUM('ALL', 'SMOKER', 'BOTH', 'VIC') NOT NULL DEFAULT 'ALL',
    category VARCHAR(50) NOT NULL COMMENT '分类名称',
    keyword VARCHAR(100) NOT NULL COMMENT '关键词',
    count INT NOT NULL DEFAULT 0 COMMENT '出现次数',
    percentage DECIMAL(5,2) NOT NULL DEFAULT 0.00 COMMENT '占比百分比',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- 索引
    UNIQUE KEY uk_buyer_category_keyword (buyer_type, category, keyword),
    INDEX idx_buyer_type (buyer_type),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='关键词分析缓存表';

-- 分类分布缓存表
CREATE TABLE IF NOT EXISTS category_distribution_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    buyer_type ENUM('ALL', 'SMOKER', 'BOTH', 'VIC') NOT NULL DEFAULT 'ALL',
    category VARCHAR(50) NOT NULL COMMENT '分类名称',
    count INT NOT NULL DEFAULT 0 COMMENT '消息数',
    percentage DECIMAL(5,2) NOT NULL DEFAULT 0.00 COMMENT '占比百分比',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- 索引
    UNIQUE KEY uk_buyer_category (buyer_type, category),
    INDEX idx_buyer_type (buyer_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分类分布缓存表';

-- 分析元数据表
CREATE TABLE IF NOT EXISTS keyword_analysis_meta (
    id INT AUTO_INCREMENT PRIMARY KEY,
    buyer_type ENUM('ALL', 'SMOKER', 'BOTH', 'VIC') NOT NULL DEFAULT 'ALL',
    total_messages INT NOT NULL DEFAULT 0 COMMENT '总消息数',
    analyzed_messages INT NOT NULL DEFAULT 0 COMMENT '已分析消息数',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_buyer_type (buyer_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='关键词分析元数据';
