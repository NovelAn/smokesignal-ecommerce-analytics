"""
Demo v2: 创建两张表

1. target_buyers_precomputed_history_demo (40 字段, 全部 ASOF 可算)
2. target_buyers_sentiment_history (方案 D - AI 跑过一次写一行, 不回填)
"""
import sys
import pymysql

sys.stdout.reconfigure(encoding='utf-8')

conn = pymysql.connect(
    host='rm-uf68p191h7j2o40s34o.mysql.rds.aliyuncs.com',
    port=3306,
    user='novelan',
    password='Anna069832-',
    database='dunhill',
    charset='utf8mb4'
)
cur = conn.cursor()

# ====================================
# Table 1: ASOF history (40 字段)
# ====================================
cur.execute("DROP TABLE IF EXISTS target_buyers_precomputed_history_demo")
print("[OK] drop old demo table (if exists)")

ddl_history = """
CREATE TABLE target_buyers_precomputed_history_demo (
    -- 标识
    buyer_nick VARCHAR(255) NOT NULL,

    -- 渠道/新老客 (trade_line 派生)
    channel VARCHAR(10),
    client_monthly_tag VARCHAR(50),

    -- Target 池子判定 (基于 d)
    is_smoker BOOLEAN DEFAULT FALSE,
    is_vic BOOLEAN DEFAULT FALSE,
    buyer_type VARCHAR(50),
    vip_level VARCHAR(10),

    -- 累计指标 (trade_line WHERE < d)
    historical_gmv DECIMAL(18, 2),
    historical_refund DECIMAL(18, 2),
    historical_net_sales DECIMAL(18, 2),
    total_orders INT,
    total_net_orders INT,
    refund_rate DECIMAL(5, 4),

    -- Rolling 24M (trade_line WHERE [d-24M, d))
    rolling_24m_gmv DECIMAL(18, 2),
    rolling_24m_netsales DECIMAL(18, 2),
    rolling_24m_orders INT,
    rolling_24m_net_orders INT,

    -- L6M (trade_line WHERE [d-6M, d))
    l6m_netsales DECIMAL(18, 2),
    l6m_gmv DECIMAL(18, 2),
    l6m_orders INT,
    l6m_refund_rate DECIMAL(5, 4),

    -- L1Y (trade_line WHERE [d-12M, d))
    l1y_netsales DECIMAL(18, 2),
    l1y_gmv DECIMAL(18, 2),
    l1y_orders INT,
    l1y_refund_rate DECIMAL(5, 4),

    -- 频率
    avg_purchase_interval_days DECIMAL(10, 2),

    -- 折扣
    discount_ratio DECIMAL(5, 2),
    discount_sensitivity VARCHAR(20),

    -- 时间边界
    first_purchase_date DATETIME,
    last_purchase_date DATETIME,

    -- 城市
    city VARCHAR(100),

    -- 品类偏好 TOP3 (按 netsales 排名)
    top_category VARCHAR(50),
    second_category VARCHAR(50),
    third_category VARCHAR(50),

    -- RFM (不依赖 chat)
    rfm_recency_score INT DEFAULT 0,
    rfm_frequency_score INT DEFAULT 0,
    rfm_monetary_score INT DEFAULT 0,
    rfm_segment VARCHAR(50),

    -- Churn (purchase-only, chat 数据不全)
    churn_risk VARCHAR(20),

    -- 时间维度
    snapshot_date DATE NOT NULL,

    PRIMARY KEY (buyer_nick, snapshot_date),
    INDEX idx_snapshot_buyer_type (snapshot_date, buyer_type),
    INDEX idx_snapshot_vip (snapshot_date, vip_level),
    INDEX idx_snapshot_date (snapshot_date),
    INDEX idx_buyer_date (buyer_nick, snapshot_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='DEMO v2 - ASOF 历史快照, trade_line 派生全部字段, 不含 AI/chat';
"""
cur.execute(ddl_history)
print("[OK] target_buyers_precomputed_history_demo v2 已创建 (40 字段)")

# ====================================
# Table 2: AI sentiment history (方案 D, 不回填)
# ====================================
cur.execute("DROP TABLE IF EXISTS target_buyers_sentiment_history_demo")
ddl_sentiment = """
CREATE TABLE target_buyers_sentiment_history_demo (
    buyer_nick VARCHAR(255) NOT NULL,
    ai_run_at DATETIME NOT NULL COMMENT 'AI 真正运行的时间',
    sentiment_label VARCHAR(20),
    sentiment_score DECIMAL(3,2),
    dominant_intent VARCHAR(50),
    pre_sale_score INT DEFAULT 0,
    post_sale_score INT DEFAULT 0,
    complaint_tendency VARCHAR(10),
    analysis_method VARCHAR(50) COMMENT 'deepseek-v4-flash / glm-4.7 / rule-based 等',

    PRIMARY KEY (buyer_nick, ai_run_at),
    INDEX idx_buyer (buyer_nick),
    INDEX idx_ai_run_at (ai_run_at),
    INDEX idx_label (sentiment_label)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='DEMO v2 - AI sentiment history, 仅 AI 跑过该买家时写入一行';
"""
cur.execute(ddl_sentiment)
print("[OK] target_buyers_sentiment_history_demo 已创建 (方案 D, AI snapshot 时刻)")

# 验证
cur.execute("SHOW TABLES LIKE 'target_buyers_precomputed_history_demo'")
print(f"\n[INFO] target_buyers_precomputed_history_demo: {'存在' if cur.fetchone() else '缺失'}")
cur.execute("SHOW TABLES LIKE 'target_buyers_sentiment_history_demo'")
print(f"[INFO] target_buyers_sentiment_history_demo: {'存在' if cur.fetchone() else '缺失'}")

cur.execute("DESCRIBE target_buyers_precomputed_history_demo")
print(f"\n[INFO] history v2 表结构 ({cur.rowcount} 列):")
for row in cur.fetchall():
    print(f"  {row[0]:<30} {row[1]}")

conn.commit()
conn.close()
print("\n[DONE] demo v2 表创建完成")
