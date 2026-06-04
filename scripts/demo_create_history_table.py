"""
Demo: 创建 target_buyers_precomputed_history_demo 表
不创建 partition, 不创建 event, 不影响主表
"""
import pymysql

conn = pymysql.connect(
    host='rm-uf68p191h7j2o40s34o.mysql.rds.aliyuncs.com',
    port=3306,
    user='novelan',
    password='Anna069832-',
    database='dunhill',
    charset='utf8mb4'
)
cur = conn.cursor()

# 先 drop（如果上次跑过）
cur.execute("DROP TABLE IF EXISTS target_buyers_precomputed_history_demo")

ddl = """
CREATE TABLE target_buyers_precomputed_history_demo (
    buyer_nick VARCHAR(255) NOT NULL,

    channel VARCHAR(10),
    client_monthly_tag VARCHAR(50),
    buyer_type VARCHAR(50),
    is_smoker BOOLEAN DEFAULT FALSE,
    is_vic BOOLEAN DEFAULT FALSE,
    vip_level VARCHAR(10),

    historical_gmv DECIMAL(18, 2),
    historical_net_sales DECIMAL(18, 2),
    total_orders INT,

    rolling_24m_netsales DECIMAL(18, 2),
    rolling_24m_orders INT,

    l6m_netsales DECIMAL(18, 2),
    l6m_orders INT,
    l1y_netsales DECIMAL(18, 2),
    l1y_orders INT,

    churn_risk VARCHAR(20),
    last_purchase_date DATETIME,
    last_chat_date DATETIME,
    chat_frequency_days INT,
    l30d_chat_frequency_days INT,

    sentiment_label VARCHAR(20),
    sentiment_score DECIMAL(3,2),
    dominant_intent VARCHAR(50),

    snapshot_date DATE NOT NULL,

    PRIMARY KEY (buyer_nick, snapshot_date),
    INDEX idx_snapshot_buyer_type (snapshot_date, buyer_type),
    INDEX idx_snapshot_vip (snapshot_date, vip_level),
    INDEX idx_snapshot_sentiment (snapshot_date, sentiment_label),
    INDEX idx_snapshot_date (snapshot_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='DEMO - 历史快照表结构测试, 不进生产';
"""
cur.execute(ddl)
conn.commit()
print("[OK] target_buyers_precomputed_history_demo 已创建")

# 验证结构
cur.execute("DESCRIBE target_buyers_precomputed_history_demo")
print(f"\n[INFO] 表结构 ({cur.rowcount} 列):")
for row in cur.fetchall():
    print(f"  {row[0]:<28} {row[1]}")

conn.close()
