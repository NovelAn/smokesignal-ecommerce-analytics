"""
Demo: Backfill 7 天历史快照到 target_buyers_precomputed_history_demo
日期范围: 2025-04-01 -> 2025-04-07

对每天 d:
  - 复制主表的静态字段 (buyer_nick, channel, buyer_type, vip_level 等)
  - 重算 rolling 窗口 (rolling_24m, l6m, l1y) 截止 d
  - sentiment_label = 'Unknown' (不调 AI)
  - snapshot_date = d

不影响主表 target_buyers_precomputed.
"""
import sys
import pymysql
from datetime import date, timedelta

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

START = date(2025, 4, 1)
END = date(2025, 4, 7)

print(f"[DEMO] backfill 范围: {START} -> {END} (共 {(END-START).days+1} 天)")
print(f"[DEMO] 目标表: target_buyers_precomputed_history_demo")
print()

# 清空历史 demo 数据
cur.execute("DELETE FROM target_buyers_precomputed_history_demo")
print(f"[INFO] 清空旧 demo 数据")
print()

# 对每天 d, 跑 INSERT ... SELECT
for offset in range((END - START).days + 1):
    d = START + timedelta(days=offset)
    d_str = d.strftime('%Y-%m-%d')
    print(f"[DAY {offset+1}/7] snapshot_date = {d_str}")

    # 1. 准备临时表存滚动指标（per buyer_nick, as_of_date = d）
    cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_rolling_demo")
    cur.execute("""
        CREATE TEMPORARY TABLE tmp_rolling_demo (
            buyer_nick VARCHAR(255) PRIMARY KEY,
            rolling_24m_netsales DECIMAL(18,2),
            rolling_24m_orders INT,
            l6m_netsales DECIMAL(18,2),
            l6m_orders INT,
            l1y_netsales DECIMAL(18,2),
            l1y_orders INT,
            last_purchase_date DATETIME
        )
    """)

    # 2. 从 trade_line 反向重算截止 d 的滚动窗口
    #    注意: 只看 < d 的付款, 即那一天之前的交易
    cur.execute("""
        INSERT INTO tmp_rolling_demo
        SELECT
            买家昵称,
            SUM(CASE WHEN 最后付款时间 >= DATE_SUB(%s, INTERVAL 24 MONTH)
                      AND 最后付款时间 < %s
                     THEN (成交总金额 - IFNULL(退款金额, 0)) ELSE 0 END) as r24_ns,
            COUNT(DISTINCT CASE WHEN 最后付款时间 >= DATE_SUB(%s, INTERVAL 24 MONTH)
                                 AND 最后付款时间 < %s
                                THEN 订单号 END) as r24_o,
            SUM(CASE WHEN 最后付款时间 >= DATE_SUB(%s, INTERVAL 6 MONTH)
                      AND 最后付款时间 < %s
                     THEN (成交总金额 - IFNULL(退款金额, 0)) ELSE 0 END) as l6_ns,
            COUNT(DISTINCT CASE WHEN 最后付款时间 >= DATE_SUB(%s, INTERVAL 6 MONTH)
                                 AND 最后付款时间 < %s
                                THEN 订单号 END) as l6_o,
            SUM(CASE WHEN 最后付款时间 >= DATE_SUB(%s, INTERVAL 12 MONTH)
                      AND 最后付款时间 < %s
                     THEN (成交总金额 - IFNULL(退款金额, 0)) ELSE 0 END) as l1_ns,
            COUNT(DISTINCT CASE WHEN 最后付款时间 >= DATE_SUB(%s, INTERVAL 12 MONTH)
                                 AND 最后付款时间 < %s
                                THEN 订单号 END) as l1_o,
            MAX(最后付款时间) as last_p
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 IN (SELECT buyer_nick FROM target_buyers_precomputed)
          AND 买家昵称 IS NOT NULL AND 买家昵称 != ''
          AND 最后付款时间 < %s
        GROUP BY 买家昵称
    """, (d, d, d, d, d, d, d, d, d, d, d, d, d))
    rolling_count = cur.rowcount

    # 3. 复制主表 + join 滚动指标, INSERT 到 demo 表
    cur.execute("""
        INSERT INTO target_buyers_precomputed_history_demo
        SELECT
            tb.buyer_nick,
            tb.channel,
            tb.client_monthly_tag,
            tb.buyer_type,
            tb.is_smoker,
            tb.is_vic,
            tb.vip_level,
            tb.historical_gmv,
            tb.historical_net_sales,
            tb.total_orders,
            COALESCE(r.rolling_24m_netsales, 0),
            COALESCE(r.rolling_24m_orders, 0),
            COALESCE(r.l6m_netsales, 0),
            COALESCE(r.l6m_orders, 0),
            COALESCE(r.l1y_netsales, 0),
            COALESCE(r.l1y_orders, 0),
            tb.churn_risk,
            r.last_purchase_date,
            tb.last_chat_date,
            tb.chat_frequency_days,
            0 as l30d_chat_frequency_days,
            'Unknown' as sentiment_label,
            NULL as sentiment_score,
            NULL as dominant_intent,
            %s as snapshot_date
        FROM target_buyers_precomputed tb
        LEFT JOIN tmp_rolling_demo r ON tb.buyer_nick = r.buyer_nick
    """, (d,))
    inserted = cur.rowcount

    conn.commit()
    print(f"  -> rolling 指标覆盖 {rolling_count} 个买家")
    print(f"  -> snapshot 写入 {inserted} 行")
    print()

cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_rolling_demo")

# 验证
cur.execute("SELECT COUNT(*), COUNT(DISTINCT buyer_nick), COUNT(DISTINCT snapshot_date) FROM target_buyers_precomputed_history_demo")
total, distinct_buyers, distinct_dates = cur.fetchone()
print(f"[VERIFY] 总行数: {total}")
print(f"[VERIFY] 不同 buyer_nick: {distinct_buyers}")
print(f"[VERIFY] 不同 snapshot_date: {distinct_dates}")

# 按日期分布
cur.execute("SELECT snapshot_date, COUNT(*) FROM target_buyers_precomputed_history_demo GROUP BY snapshot_date ORDER BY snapshot_date")
print(f"\n[VERIFY] 按日期分布:")
for row in cur.fetchall():
    print(f"  {row[0]}  -> {row[1]} 行")

conn.close()
print("\n[DEMO] backfill 完成!")
