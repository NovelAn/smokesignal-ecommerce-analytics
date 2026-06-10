"""
Demo v2: 真 ASOF backfill 7 天到 target_buyers_precomputed_history_demo

对每天 d:
  1. 识别 target 池子 (Smoker + VIC 真实判定)
  2. 重算所有 trade_line 派生指标 (40 字段)
  3. INSERT 到 history_demo

不复用主表 target_buyers_precomputed (因为它代表今天的状态, 不是 d 的状态)
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
END = date(2025, 4, 30)

print(f"[DEMO v2] backfill 范围: {START} -> {END} ({(END-START).days+1} 天)")
print(f"[DEMO v2] 真 ASOF: 每天重新识别 target 池子 + 重算 40 字段")
print()

# 清空
cur.execute("DELETE FROM target_buyers_precomputed_history_demo")
print(f"[INFO] 清空历史 demo 数据\n")

# Pre-check: 多少买家在 START 之前买过 Pipes/Lighters
cur.execute("""
    SELECT COUNT(DISTINCT 买家昵称) FROM dunhill_t01_trade_line
    WHERE category IN ('Pipes', 'Lighters')
      AND 买家昵称 IS NOT NULL AND 买家昵称 != ''
""")
smoker_total = cur.fetchone()[0]
print(f"[PRE-CHECK] 总共 {smoker_total} 个买家在历史上买过 Pipes/Lighters (候选 Smoker 池)")
print()

def backfill_day(d):
    d_str = d.strftime('%Y-%m-%d')
    print(f"[DAY] snapshot_date = {d_str}")

    # ---- Step 1: 识别 target 池子 ----
    cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_target")
    cur.execute("""
        CREATE TEMPORARY TABLE tmp_target (
            buyer_nick VARCHAR(255) PRIMARY KEY,
            is_smoker TINYINT(1),
            is_vic TINYINT(1),
            buyer_type VARCHAR(50)
        )
    """)

    # Smoker: 在 d 之前买过 Pipes/Lighters (关键: 加 < d 过滤, 否则会包含未来才买的客户)
    cur.execute("""
        INSERT IGNORE INTO tmp_target (buyer_nick, is_smoker, is_vic, buyer_type)
        SELECT DISTINCT 买家昵称, 1, 0, 'SMOKER'
        FROM dunhill_t01_trade_line
        WHERE category IN ('Pipes', 'Lighters')
          AND 买家昵称 IS NOT NULL AND 买家昵称 != ''
          AND 最后付款时间 < %s
    """, (d,))
    smoker_added = cur.rowcount

    # VIC: 截止 d 往前 rolling 24M 净销售 >= 30K
    cur.execute("""
        INSERT INTO tmp_target (buyer_nick, is_smoker, is_vic, buyer_type)
        SELECT 买家昵称, 0, 1, 'VIC'
        FROM dunhill_t01_trade_line
        WHERE 最后付款时间 < %s
          AND 最后付款时间 >= DATE_SUB(%s, INTERVAL 24 MONTH)
          AND 买家昵称 IS NOT NULL AND 买家昵称 != ''
        GROUP BY 买家昵称
        HAVING SUM(成交总金额 - IFNULL(退款金额, 0)) >= 30000
        ON DUPLICATE KEY UPDATE is_vic=1, buyer_type='BOTH'
    """, (d, d))
    vic_added = cur.rowcount

    cur.execute("SELECT COUNT(*) FROM tmp_target")
    target_count = cur.fetchone()[0]
    print(f"  target 池: {target_count} 人 (新增 smoker={smoker_added}, vic={vic_added})")

    # ---- Step 2: 计算所有派生指标 ----
    # 用 4 个 temp table: cumulative / rolling24m / l6m / l1y
    # 然后 final INSERT JOIN 起来

    # 2a. 累计 (< d)
    # NOTE: 此处 MAX(client_monthly_tag) 保留作为历史 demo 阶段产物, 不再使用.
    #       生产 procedure (snapshot_target_buyers_history / refresh_target_buyers_asof)
    #       已改用 ROW_NUMBER() 取 d 之前最近一次购买时的 tag.
    #       此 demo 脚本仅作为 PR1 前的探索阶段产物保留, 不参与 production.
    cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_cum")
    cur.execute("""
        CREATE TEMPORARY TABLE tmp_cum (
            buyer_nick VARCHAR(255) PRIMARY KEY,
            channel VARCHAR(10),
            client_monthly_tag VARCHAR(50),
            city VARCHAR(100),
            first_purchase_date DATETIME,
            last_purchase_date DATETIME,
            historical_gmv DECIMAL(18,2),
            historical_refund DECIMAL(18,2),
            historical_net_sales DECIMAL(18,2),
            total_orders INT,
            refunded_orders INT
        )
    """)
    cur.execute("""
        INSERT INTO tmp_cum
        SELECT
            买家昵称,
            MAX(CASE WHEN channel IS NOT NULL THEN channel END),
            MAX(client_monthly_tag),
            MAX(城市),
            MIN(最后付款时间),
            MAX(最后付款时间),
            SUM(成交总金额),
            SUM(IFNULL(退款金额, 0)),
            SUM(成交总金额 - IFNULL(退款金额, 0)),
            COUNT(DISTINCT 订单号),
            COUNT(DISTINCT CASE WHEN 退款金额 > 0 THEN 订单号 END)
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 IN (SELECT buyer_nick FROM tmp_target)
          AND 最后付款时间 < %s
        GROUP BY 买家昵称
    """, (d,))

    # 2b. Rolling 24M
    cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_r24")
    cur.execute("""
        CREATE TEMPORARY TABLE tmp_r24 (
            buyer_nick VARCHAR(255) PRIMARY KEY,
            rolling_24m_gmv DECIMAL(18,2),
            rolling_24m_netsales DECIMAL(18,2),
            rolling_24m_orders INT,
            rolling_24m_refund DECIMAL(18,2)
        )
    """)
    cur.execute("""
        INSERT INTO tmp_r24
        SELECT
            买家昵称,
            SUM(成交总金额),
            SUM(成交总金额 - IFNULL(退款金额, 0)),
            COUNT(DISTINCT 订单号),
            SUM(IFNULL(退款金额, 0))
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 IN (SELECT buyer_nick FROM tmp_target)
          AND 最后付款时间 < %s
          AND 最后付款时间 >= DATE_SUB(%s, INTERVAL 24 MONTH)
        GROUP BY 买家昵称
    """, (d, d))

    # 2c. L6M
    cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_l6m")
    cur.execute("""
        CREATE TEMPORARY TABLE tmp_l6m (
            buyer_nick VARCHAR(255) PRIMARY KEY,
            l6m_gmv DECIMAL(18,2),
            l6m_netsales DECIMAL(18,2),
            l6m_orders INT,
            l6m_refund DECIMAL(18,2)
        )
    """)
    cur.execute("""
        INSERT INTO tmp_l6m
        SELECT
            买家昵称,
            SUM(成交总金额),
            SUM(成交总金额 - IFNULL(退款金额, 0)),
            COUNT(DISTINCT 订单号),
            SUM(IFNULL(退款金额, 0))
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 IN (SELECT buyer_nick FROM tmp_target)
          AND 最后付款时间 < %s
          AND 最后付款时间 >= DATE_SUB(%s, INTERVAL 6 MONTH)
        GROUP BY 买家昵称
    """, (d, d))

    # 2d. L1Y
    cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_l1y")
    cur.execute("""
        CREATE TEMPORARY TABLE tmp_l1y (
            buyer_nick VARCHAR(255) PRIMARY KEY,
            l1y_gmv DECIMAL(18,2),
            l1y_netsales DECIMAL(18,2),
            l1y_orders INT,
            l1y_refund DECIMAL(18,2)
        )
    """)
    cur.execute("""
        INSERT INTO tmp_l1y
        SELECT
            买家昵称,
            SUM(成交总金额),
            SUM(成交总金额 - IFNULL(退款金额, 0)),
            COUNT(DISTINCT 订单号),
            SUM(IFNULL(退款金额, 0))
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 IN (SELECT buyer_nick FROM tmp_target)
          AND 最后付款时间 < %s
          AND 最后付款时间 >= DATE_SUB(%s, INTERVAL 12 MONTH)
        GROUP BY 买家昵称
    """, (d, d))

    # 2e. 折扣敏感度
    cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_discount")
    cur.execute("""
        CREATE TEMPORARY TABLE tmp_discount (
            buyer_nick VARCHAR(255) PRIMARY KEY,
            discount_ratio DECIMAL(5,2)
        )
    """)
    cur.execute("""
        INSERT INTO tmp_discount
        SELECT
            买家昵称,
            CAST(SUM(CASE WHEN FP_MD = 'MD' THEN 1 ELSE 0 END) AS DECIMAL(10,2))
                / NULLIF(COUNT(DISTINCT 订单号), 0)
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 IN (SELECT buyer_nick FROM tmp_target)
          AND 最后付款时间 < %s
        GROUP BY 买家昵称
    """, (d,))

    # 2f. 品类 TOP3 (按 netsales)
    cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_cat")
    cur.execute("""
        CREATE TEMPORARY TABLE tmp_cat (
            buyer_nick VARCHAR(255),
            category VARCHAR(50),
            cat_netsales DECIMAL(18,2),
            rank_num INT,
            PRIMARY KEY (buyer_nick, rank_num)
        )
    """)
    cur.execute("""
        INSERT INTO tmp_cat
        SELECT buyer_nick, category, cat_netsales, rank_num FROM (
            SELECT
                买家昵称 as buyer_nick,
                category,
                SUM(成交总金额 - IFNULL(退款金额, 0)) as cat_netsales,
                ROW_NUMBER() OVER (PARTITION BY 买家昵称 ORDER BY SUM(成交总金额 - IFNULL(退款金额, 0)) DESC) as rank_num
            FROM dunhill_t01_trade_line
            WHERE 买家昵称 IN (SELECT buyer_nick FROM tmp_target)
              AND 最后付款时间 < %s
              AND category IS NOT NULL AND category != ''
            GROUP BY 买家昵称, category
        ) ranked
        WHERE rank_num <= 3
    """, (d,))

    # ---- Step 3: Final INSERT ----
    # 用 CTE 把 R/F/M 算成 base.r_score/f_score/m_score, 外层 segment + churn 引用
    cur.execute("""
        INSERT INTO target_buyers_precomputed_history_demo
        WITH base AS (
            SELECT
                t.buyer_nick,
                cum.channel,
                cum.client_monthly_tag,
                t.is_smoker,
                t.is_vic,
                t.buyer_type,
                CASE
                    WHEN COALESCE(r24.rolling_24m_netsales, 0) >= 450000 THEN 'V3'
                    WHEN COALESCE(r24.rolling_24m_netsales, 0) >= 150000 THEN 'V2'
                    WHEN COALESCE(r24.rolling_24m_netsales, 0) >= 50000  THEN 'V1'
                    WHEN COALESCE(r24.rolling_24m_netsales, 0) >= 30000  THEN 'V0'
                    ELSE 'Non-VIP'
                END as vip_level,
                COALESCE(cum.historical_gmv, 0) as historical_gmv,
                COALESCE(cum.historical_refund, 0) as historical_refund,
                COALESCE(cum.historical_net_sales, 0) as historical_net_sales,
                COALESCE(cum.total_orders, 0) as total_orders,
                COALESCE(cum.total_orders, 0) - COALESCE(cum.refunded_orders, 0) as total_net_orders,
                CASE WHEN COALESCE(cum.historical_gmv, 0) > 0
                     THEN cum.historical_refund / cum.historical_gmv ELSE 0 END as refund_rate,
                COALESCE(r24.rolling_24m_gmv, 0) as rolling_24m_gmv,
                COALESCE(r24.rolling_24m_netsales, 0) as rolling_24m_netsales,
                COALESCE(r24.rolling_24m_orders, 0) as rolling_24m_orders,
                COALESCE(r24.rolling_24m_orders, 0) - COALESCE((
                    SELECT COUNT(DISTINCT 订单号) FROM dunhill_t01_trade_line
                    WHERE 买家昵称 = t.buyer_nick
                      AND 最后付款时间 < %s
                      AND 最后付款时间 >= DATE_SUB(%s, INTERVAL 24 MONTH)
                      AND 退款金额 > 0
                ), 0) as rolling_24m_net_orders,
                COALESCE(l6m.l6m_netsales, 0) as l6m_netsales,
                COALESCE(l6m.l6m_gmv, 0) as l6m_gmv,
                COALESCE(l6m.l6m_orders, 0) as l6m_orders,
                CASE WHEN COALESCE(l6m.l6m_gmv, 0) > 0
                     THEN COALESCE(l6m.l6m_refund, 0) / l6m.l6m_gmv ELSE 0 END as l6m_refund_rate,
                COALESCE(l1y.l1y_netsales, 0) as l1y_netsales,
                COALESCE(l1y.l1y_gmv, 0) as l1y_gmv,
                COALESCE(l1y.l1y_orders, 0) as l1y_orders,
                CASE WHEN COALESCE(l1y.l1y_gmv, 0) > 0
                     THEN COALESCE(l1y.l1y_refund, 0) / l1y.l1y_gmv ELSE 0 END as l1y_refund_rate,
                CASE WHEN COALESCE(cum.total_orders, 0) > 0
                          AND DATEDIFF(cum.last_purchase_date, cum.first_purchase_date) > 0
                     THEN DATEDIFF(cum.last_purchase_date, cum.first_purchase_date) / cum.total_orders
                     ELSE 0 END as avg_purchase_interval_days,
                COALESCE(disc.discount_ratio, 0) as discount_ratio,
                CASE
                    WHEN COALESCE(disc.discount_ratio, 0) >= 0.7 THEN '高度敏感'
                    WHEN COALESCE(disc.discount_ratio, 0) >= 0.4 THEN '中度敏感'
                    ELSE '低度敏感'
                END as discount_sensitivity,
                cum.first_purchase_date,
                cum.last_purchase_date,
                cum.city,
                cats.top_cat,
                cats.second_cat,
                cats.third_cat,
                -- R/F/M scores (主表 refresh procedure 同款阈值, ASOF 基于 d)
                CASE
                    WHEN cum.last_purchase_date IS NULL THEN 0
                    WHEN DATEDIFF(%s, cum.last_purchase_date) <= 60  THEN 5
                    WHEN DATEDIFF(%s, cum.last_purchase_date) <= 180 THEN 4
                    WHEN DATEDIFF(%s, cum.last_purchase_date) <= 365 THEN 3
                    WHEN DATEDIFF(%s, cum.last_purchase_date) <= 730 THEN 2
                    ELSE 1
                END as r_score,
                CASE
                    WHEN cum.total_orders >= 5 THEN 5
                    WHEN cum.total_orders >= 3 THEN 4
                    WHEN cum.total_orders = 2 THEN 3
                    WHEN cum.total_orders = 1 THEN 1
                    ELSE 0
                END as f_score,
                CASE
                    WHEN cum.historical_net_sales >= 50000 THEN 5
                    WHEN cum.historical_net_sales >= 20000 THEN 4
                    WHEN cum.historical_net_sales >= 10000 THEN 3
                    WHEN cum.historical_net_sales >= 5000  THEN 2
                    ELSE 1
                END as m_score
            FROM tmp_target t
            LEFT JOIN tmp_cum cum ON t.buyer_nick = cum.buyer_nick
            LEFT JOIN tmp_r24 r24 ON t.buyer_nick = r24.buyer_nick
            LEFT JOIN tmp_l6m l6m ON t.buyer_nick = l6m.buyer_nick
            LEFT JOIN tmp_l1y l1y ON t.buyer_nick = l1y.buyer_nick
            LEFT JOIN tmp_discount disc ON t.buyer_nick = disc.buyer_nick
            LEFT JOIN (
                SELECT buyer_nick,
                    MAX(CASE WHEN rank_num = 1 THEN category END) as top_cat,
                    MAX(CASE WHEN rank_num = 2 THEN category END) as second_cat,
                    MAX(CASE WHEN rank_num = 3 THEN category END) as third_cat
                FROM tmp_cat GROUP BY buyer_nick
            ) cats ON t.buyer_nick = cats.buyer_nick
        )
        SELECT
            base.buyer_nick,
            base.channel,
            base.client_monthly_tag,
            base.is_smoker,
            base.is_vic,
            base.buyer_type,
            base.vip_level,
            base.historical_gmv,
            base.historical_refund,
            base.historical_net_sales,
            base.total_orders,
            base.total_net_orders,
            base.refund_rate,
            base.rolling_24m_gmv,
            base.rolling_24m_netsales,
            base.rolling_24m_orders,
            base.rolling_24m_net_orders,
            base.l6m_netsales,
            base.l6m_gmv,
            base.l6m_orders,
            base.l6m_refund_rate,
            base.l1y_netsales,
            base.l1y_gmv,
            base.l1y_orders,
            base.l1y_refund_rate,
            base.avg_purchase_interval_days,
            base.discount_ratio,
            base.discount_sensitivity,
            base.first_purchase_date,
            base.last_purchase_date,
            base.city,
            base.top_cat,
            base.second_cat,
            base.third_cat,
            base.r_score,
            base.f_score,
            base.m_score,
            -- 13 类主表同款 segment (用 R/F/M 数值)
            CASE
                WHEN base.m_score >= 4 AND base.r_score >= 4 AND base.f_score >= 4 THEN '重要价值客户'
                WHEN base.m_score >= 4 AND base.r_score >= 4 AND base.f_score <= 3 THEN '重要发展客户'
                WHEN base.m_score >= 4 AND base.r_score <= 3 AND base.f_score >= 4 THEN '重要保持客户'
                WHEN base.m_score >= 4 AND base.r_score <= 3 AND base.f_score <= 3 THEN '重要挽留客户'
                WHEN base.m_score = 3 AND base.r_score >= 4 AND base.f_score >= 4 THEN '优质价值客户'
                WHEN base.m_score = 3 AND base.r_score >= 4 AND base.f_score <= 3 THEN '优质发展客户'
                WHEN base.m_score = 3 AND base.r_score <= 3 AND base.f_score >= 4 THEN '优质保持客户'
                WHEN base.m_score = 3 AND base.r_score <= 3 AND base.f_score <= 3 THEN '优质挽留客户'
                WHEN base.m_score = 2 AND base.r_score >= 4 THEN '潜力客户'
                WHEN base.m_score = 2 AND base.r_score <= 3 THEN '待激活客户'
                WHEN base.m_score = 1 AND base.r_score >= 4 THEN '新客户'
                WHEN base.m_score = 1 AND base.r_score IN (2, 3) THEN '低价值客户'
                WHEN base.r_score = 1 THEN '已流失'
                WHEN base.r_score = 0 THEN '无购买记录'
            END,
            -- Churn risk: R + F 组合 (用户决策, 不依赖 chat)
            CASE
                WHEN base.last_purchase_date IS NULL THEN '低'
                WHEN base.r_score = 1 THEN '高'
                WHEN base.r_score = 2 THEN '高'
                WHEN base.r_score = 3 AND base.f_score >= 4 THEN '中'
                WHEN base.r_score = 3 THEN '中'
                WHEN base.r_score = 4 AND base.f_score <= 2 THEN '中'
                ELSE '低'
            END,
            %s as snapshot_date
        FROM base
    """, (d, d, d, d, d, d, d))
    inserted = cur.rowcount

    conn.commit()
    print(f"  -> INSERT {inserted} 行\n")

# 主循环
for offset in range((END - START).days + 1):
    backfill_day(START + timedelta(days=offset))

# 清理
for t in ['tmp_target', 'tmp_cum', 'tmp_r24', 'tmp_l6m', 'tmp_l1y', 'tmp_discount', 'tmp_cat']:
    cur.execute(f"DROP TEMPORARY TABLE IF EXISTS {t}")

# 验证
cur.execute("SELECT COUNT(*), COUNT(DISTINCT buyer_nick), COUNT(DISTINCT snapshot_date) FROM target_buyers_precomputed_history_demo")
total, buyers, days = cur.fetchone()
print(f"[VERIFY] 总行数: {total}")
print(f"[VERIFY] 不同买家: {buyers}")
print(f"[VERIFY] 不同 snapshot_date: {days}")

# 按日期看池子大小
cur.execute("""
    SELECT snapshot_date, buyer_type, COUNT(*) FROM target_buyers_precomputed_history_demo
    GROUP BY snapshot_date, buyer_type ORDER BY snapshot_date, buyer_type
""")
print(f"\n[VERIFY] target 池子 (按日期 + 类型):")
for r in cur.fetchall():
    print(f"  {r[0]}  {r[1]:<10}  {r[2]}")

conn.close()
print("\n[DONE] v2 backfill 完成")
