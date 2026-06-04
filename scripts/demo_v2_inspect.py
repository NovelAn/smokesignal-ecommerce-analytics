"""
Demo v2: 展示真 ASOF backfill 数据
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
cur = conn.cursor(pymysql.cursors.DictCursor)

def hr(c='-'):
    print(c * 80)

print("=" * 80)
print("STEP 1: 数据规模 - 470 个独立买家, 7 天 snapshot, 3290 行")
print("=" * 80)
cur.execute("""
    SELECT COUNT(*) as total, COUNT(DISTINCT buyer_nick) as buyers, COUNT(DISTINCT snapshot_date) as days
    FROM target_buyers_precomputed_history_demo
""")
r = cur.fetchone()
print(f"  total: {r['total']}, buyers: {r['buyers']}, days: {r['days']}")
cur.execute("""
    SELECT ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as mb
    FROM information_schema.TABLES
    WHERE TABLE_SCHEMA='dunhill' AND TABLE_NAME='target_buyers_precomputed_history_demo'
""")
size_mb = cur.fetchone()['mb']
print(f"  size: {size_mb} MB")
print(f"  [估算] 24M 保留 = {3290 / 7 * 30 * 24:,.0f} 行 ≈ {size_mb / 7 * 30 * 24:.0f} MB")

print()
hr()
print("STEP 2: 真 ASOF target 池子随日期变化")
print("(对比: 主表今天 548, 2025-04 当时只有 470)")
print("=" * 80)
cur.execute("""
    SELECT snapshot_date, buyer_type, vip_level, COUNT(*) as count
    FROM target_buyers_precomputed_history_demo
    GROUP BY snapshot_date, buyer_type, vip_level
    ORDER BY snapshot_date, buyer_type, vip_level
""")
for r in cur.fetchall():
    print(f"  {r['snapshot_date']}  {r['buyer_type']:<8}  {r['vip_level']:<10}  count={r['count']}")

print()
hr()
print("STEP 3: 抽样 1 个 BOTH 买家看 7 天真实 ASOF 变化")
print("=" * 80)
cur.execute("""
    SELECT buyer_nick, snapshot_date, buyer_type, vip_level,
           historical_net_sales, rolling_24m_netsales, l6m_netsales,
           total_orders, churn_risk, rfm_segment, top_category
    FROM target_buyers_precomputed_history_demo
    WHERE buyer_type = 'BOTH'
    ORDER BY buyer_nick, snapshot_date
    LIMIT 14
""")
prev = None
for r in cur.fetchall():
    if r['buyer_nick'] != prev:
        print()
        prev = r['buyer_nick']
        print(f"  buyer_nick: {r['buyer_nick']} (BOTH)")
    print(f"    {r['snapshot_date']}  vip={r['vip_level']:<8}  r24=¥{r['rolling_24m_netsales']:>9,.0f}  l6=¥{r['l6m_netsales']:>8,.0f}  orders={r['total_orders']:>3}  churn={r['churn_risk']}  rfm={r['rfm_segment']}  top={r['top_category']}")

print()
hr()
print("STEP 4: VIP 等级分布在 7 天内的变化")
print("=" * 80)
cur.execute("""
    SELECT snapshot_date, vip_level, COUNT(*) as count, ROUND(AVG(rolling_24m_netsales), 0) as avg_r24
    FROM target_buyers_precomputed_history_demo
    WHERE buyer_type IN ('VIC', 'BOTH')
    GROUP BY snapshot_date, vip_level
    ORDER BY snapshot_date, vip_level
""")
for r in cur.fetchall():
    print(f"  {r['snapshot_date']}  {r['vip_level']:<10}  count={r['count']:>4}  avg_r24=¥{r['avg_r24']:>10,.0f}")

print()
hr()
print("STEP 5: 真实 YoY 模拟 - 拿 04-01~04-03 跟 04-04~04-07 对比")
print("=" * 80)
cur.execute("""
    SELECT
        CASE WHEN snapshot_date <= '2025-04-03' THEN 'period_1 (前 3 天)' ELSE 'period_2 (后 4 天)' END as period,
        buyer_type,
        COUNT(DISTINCT buyer_nick) as distinct_buyers,
        ROUND(AVG(rolling_24m_netsales), 0) as avg_r24,
        ROUND(AVG(l6m_netsales), 0) as avg_l6,
        ROUND(AVG(total_orders), 0) as avg_orders
    FROM target_buyers_precomputed_history_demo
    WHERE buyer_type IN ('VIC', 'BOTH')
    GROUP BY period, buyer_type
    ORDER BY period, buyer_type
""")
for r in cur.fetchall():
    print(f"  {r['period']:<22}  {r['buyer_type']:<8}  buyers={r['distinct_buyers']:>4}  avg_r24=¥{r['avg_r24']:>10,.0f}  avg_l6=¥{r['avg_l6']:>8,.0f}  avg_orders={r['avg_orders']:>3}")

print()
hr()
print("STEP 6: RFM segment 分布")
print("=" * 80)
cur.execute("""
    SELECT rfm_segment, COUNT(DISTINCT buyer_nick) as buyers
    FROM target_buyers_precomputed_history_demo
    WHERE snapshot_date = '2025-04-01'
    GROUP BY rfm_segment
    ORDER BY buyers DESC
""")
for r in cur.fetchall():
    print(f"  {r['rfm_segment']:<8}  buyers={r['buyers']}")

print()
hr()
print("STEP 7: 字段填充率 - 哪些字段 ASOF 算出来是 0/NULL 的多")
print("=" * 80)
cur.execute("""
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN historical_net_sales > 0 THEN 1 ELSE 0 END) as has_cum_sales,
        SUM(CASE WHEN rolling_24m_netsales > 0 THEN 1 ELSE 0 END) as has_r24,
        SUM(CASE WHEN l6m_netsales > 0 THEN 1 ELSE 0 END) as has_l6,
        SUM(CASE WHEN l1y_netsales > 0 THEN 1 ELSE 0 END) as has_l1,
        SUM(CASE WHEN top_category IS NOT NULL THEN 1 ELSE 0 END) as has_top_cat,
        SUM(CASE WHEN city IS NOT NULL THEN 1 ELSE 0 END) as has_city,
        SUM(CASE WHEN discount_ratio > 0 THEN 1 ELSE 0 END) as has_discount
    FROM target_buyers_precomputed_history_demo
    WHERE snapshot_date = '2025-04-01'
""")
r = cur.fetchone()
total = r['total']
print(f"  total = {total}")
for k, v in r.items():
    if k == 'total': continue
    pct = float(v) * 100.0 / total if total else 0
    print(f"  {k:<18}  {v:>4}/{total}  ({pct:.1f}%)")

print()
hr()
print("STEP 8: sentiment_history 表 (方案 D) - DDL 已建, 数据待 AI 跑后写入")
print("=" * 80)
cur.execute("SELECT COUNT(*) as cnt FROM target_buyers_sentiment_history_demo")
print(f"  当前行数: {cur.fetchone()['cnt']} (预期 0, 等 AI 任务触发)")

print()
hr()
print("STEP 9: 主表未受影响")
print("=" * 80)
cur.execute("SELECT COUNT(*) as cnt, MAX(updated_at) as last_upd FROM target_buyers_precomputed")
r = cur.fetchone()
print(f"  target_buyers_precomputed 主表: {r['cnt']} 行, updated_at={r['last_upd']}")

conn.close()
print()
print("[DONE] v2 展示完成")
