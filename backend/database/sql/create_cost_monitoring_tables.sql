-- Cost Monitoring Tables for AI Analysis System
-- Deploy this to enable persistent cost tracking and historical analysis

-- Table 1: AI Cost Log (Individual API call records)
CREATE TABLE IF NOT EXISTS ai_cost_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    model VARCHAR(50) NOT NULL COMMENT 'deepseek-reasoner, deepseek-chat, glm-4-plus, etc.',
    input_tokens INT NOT NULL COMMENT 'Input prompt tokens',
    output_tokens INT NOT NULL COMMENT 'Output response tokens',
    total_tokens INT NOT NULL COMMENT 'Total tokens used',
    cost DECIMAL(10, 4) NOT NULL COMMENT 'Cost in CNY',
    buyer_nick VARCHAR(100) COMMENT 'Buyer nickname (optional)',
    method VARCHAR(50) COMMENT 'Analysis method (e.g., DeepSeek-R1, Zhipu-GLM)',
    INDEX idx_timestamp (timestamp),
    INDEX idx_buyer_nick (buyer_nick),
    INDEX idx_model (model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI API cost log - individual call records';

-- Table 2: AI Cost Daily Summary (Aggregated daily statistics)
CREATE TABLE IF NOT EXISTS ai_cost_daily_summary (
    date DATE PRIMARY KEY COMMENT 'Summary date',
    total_calls INT NOT NULL DEFAULT 0 COMMENT 'Total API calls',
    total_cost DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT 'Total cost in CNY',
    deepseek_r1_calls INT NOT NULL DEFAULT 0 COMMENT 'DeepSeek-R1 calls',
    deepseek_r1_cost DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT 'DeepSeek-R1 cost',
    deepseek_chat_calls INT NOT NULL DEFAULT 0 COMMENT 'DeepSeek-Chat calls',
    deepseek_chat_cost DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT 'DeepSeek-Chat cost',
    zhipu_calls INT NOT NULL DEFAULT 0 COMMENT 'Zhipu GLM calls',
    zhipu_cost DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT 'Zhipu GLM cost',
    budget DECIMAL(10, 2) NOT NULL DEFAULT 50.00 COMMENT 'Daily budget in CNY',
    budget_usage_rate DECIMAL(5, 2) NOT NULL DEFAULT 0.00 COMMENT 'Budget usage percentage (0-100)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI cost daily summary - aggregated statistics';

-- Table 3: AI Cost Hourly Breakdown (For hourly cost charts)
CREATE TABLE IF NOT EXISTS ai_cost_hourly (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    hour TINYINT NOT NULL COMMENT 'Hour (0-23)',
    model VARCHAR(50) NOT NULL,
    calls INT NOT NULL DEFAULT 0,
    cost DECIMAL(10, 4) NOT NULL DEFAULT 0.0000,
    tokens INT NOT NULL DEFAULT 0,
    UNIQUE KEY idx_date_hour_model (date, hour, model),
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI cost hourly breakdown - for time-series charts';

-- Insert initial today's summary if not exists
INSERT IGNORE INTO ai_cost_daily_summary (date, total_calls, total_cost, budget)
VALUES (CURDATE(), 0, 0.00, 50.00);
