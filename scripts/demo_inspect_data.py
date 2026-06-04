"""
Demo: 展示 backfill 数据 + 验证查询样例
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
print("STEP 1: 按 buyer_type + snapshot_date 看 VIC 池子大小 (7 天趋势)")
print("=" * 80)
cur.execute("""
    SELECT snapshot_date, buyer_type, COUNT(*) as count, SUM(rolling_24m_netsales) as total_r24
    FROM target_buyers_precomputed_history_demo
    WHERE buyer_type IN ('VIC', 'BOTH')
    GROUP BY snapshot_date, buyer_type
    ORDER BY snapshot_date, buyer_type
""")
for r in cur.fetchall():
    print(f"  {r['snapshot_date']}  {r['buyer_type']:<6}  count={r['count']:>4}  total_rolling_24m=¥{r['total_r24']:>12,.0f}")

print()
hr()
print("STEP 2: 同一买家 7 天 rolling 24M 变化 (挑一个有交易的)")
print("=" * 80)
cur.execute("""
    SELECT buyer_nick, buyer_type, snapshot_date, rolling_24m_netsales, rolling_24m_orders
    FROM target_buyers_precomputed_history_demo
    WHERE rolling_24m_orders > 0
    ORDER BY buyer_nick, snapshot_date
    LIMIT 21
""")
rows = cur.fetchall()
if rows:
    seen = set()
    for r in rows:
        if r['buyer_nick'] not in seen:
            seen.add(r['buyer_nick'])
            print(f"\n  buyer_nick: {r['buyer_nick']} ({r['buyer_type']})")
        print(f"    {r['snapshot_date']}  r24_netsales=¥{r['rolling_24m_netsales']:>10,.0f}  r24_orders={r['rolling_24m_orders']:>3}")
else:
    print("  (无 rolling 交易数据)")

print()
hr()
print("STEP 3: 模拟 YoY/MoM 查询 (跨期聚合)")
print("=" * 80)
# 我们只有 7 天数据, 假装 Q1 = 前 3 天, Q2 = 后 4 天
cur.execute("""
    SELECT
        CASE WHEN snapshot_date <= '2025-04-03' THEN 'period_1 (04-01~04-03)'
             ELSE 'period_2 (04-04~04-07)' END as period,
        buyer_type,
        COUNT(DISTINCT buyer_nick) as distinct_buyers,
        ROUND(AVG(rolling_24m_netsales), 0) as avg_r24,
        ROUND(AVG(l6m_netsales), 0) as avg_l6
    FROM target_buyers_precomputed_history_demo
    WHERE buyer_type IN ('VIC', 'BOTH')
    GROUP BY period, buyer_type
    ORDER BY period, buyer_type
""")
for r in cur.fetchall():
    print(f"  {r['period']:<28}  {r['buyer_type']:<6}  buyers={r['distinct_buyers']:>4}  avg_r24=¥{r['avg_r24']:>10,.0f}  avg_l6=¥{r['avg_l6']:>8,.0f}")

print()
hr()
print("STEP 4: 按 vip_level 分布 (7 天看 VIP 客户结构)")
print("=" * 80)
cur.execute("""
    SELECT snapshot_date, vip_level, COUNT(*) as count, ROUND(AVG(rolling_24m_netsales), 0) as avg_r24
    FROM target_buyers_precomputed_history_demo
    WHERE buyer_type IN ('VIC', 'BOTH')
    GROUP BY snapshot_date, vip_level
    ORDER BY snapshot_date, vip_level
""")
prev_date = None
for r in cur.fetchall():
    if r['snapshot_date'] != prev_date:
        print()
        prev_date = r['snapshot_date']
    print(f"  {r['snapshot_date']}  {r['vip_level']:<10}  count={r['count']:>4}  avg_r24=¥{r['avg_r24']:>10,.0f}")

print()
hr()
print("STEP 5: 数据量与索引")
print("=" * 80)
cur.execute("""
    SELECT
        TABLE_ROWS as total_rows,
        ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as size_mb
    FROM information_schema.TABLES
    WHERE TABLE_SCHEMA = 'dunhill' AND TABLE_NAME = 'target_buyers_precomputed_history_demo'
""")
r = cur.fetchone()
print(f"  估算行数 (TABLE_ROWS): {r['total_rows']:,}")
print(f"  表大小 (data+index): {r['size_mb']} MB")
cur.execute("SELECT COUNT(*) as cnt, COUNT(DISTINCT buyer_nick) as buyers, COUNT(DISTINCT snapshot_date) as days FROM target_buyers_precomputed_history_demo")
real = cur.fetchone()
print(f"  实际行数: {real['cnt']:,}")
print(f"  不同买家: {real['buyers']:,}")
print(f"  不同 snapshot_date: {real['days']}")
print()
print(f"  [估算] 24M 保留 = {real['cnt'] * 24 * 30 / 7:,.0f} 行 ≈ {r['size_mb'] * 24 * 30 / 7:.0f} MB")

print()
hr()
print("STEP 6: 表是否影响主表?")
print("=" * 80)
cur.execute("SELECT COUNT(*) as cnt FROM target_buyers_precomputed")
main_count = cur.fetchone()['cnt']
print(f"  target_buyers_precomputed (主表): {main_count} 行 (预期 548, 没变)")
cur.execute("SELECT MAX(updated_at) as last_upd FROM target_buyers_precomputed")
print(f"  主表 updated_at 最新: {cur.fetchone()['last_upd']}")

conn.close()
print()
print("[DONE] demo 展示完成")
