"""
检查数据库中日期字段的格式
"""
import pymysql

DB_CONFIG = {
    "host": "rm-uf68p191h7j2o40s34o.mysql.rds.aliyuncs.com",
    "user": "novelan",
    "password": "Anna069832-",
    "database": "dunhill",
    "port": 3306,
    "charset": "utf8mb4"
}

conn = pymysql.connect(**DB_CONFIG)

with conn.cursor(pymysql.cursors.DictCursor) as cursor:
    # 检查最后付款时间的不同格式
    print("=== 检查最后付款时间字段 ===")
    cursor.execute("""
        SELECT 最后付款时间, COUNT(*) as cnt
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 IS NOT NULL AND 买家昵称 != ''
        GROUP BY 最后付款时间
        ORDER BY cnt DESC
        LIMIT 20
    """)
    results = cursor.fetchall()
    for row in results:
        print(f"  {row['最后付款时间']} ({row['cnt']}条)")

    # 检查是否有无效的日期格式
    print("\n=== 检查无效日期 ===")
    cursor.execute("""
        SELECT 最后付款时间, COUNT(*) as cnt
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 IS NOT NULL AND 买家昵称 != ''
          AND 最后付款 time NOT REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
        GROUP BY 最后付款时间
        LIMIT 10
    """)
    results = cursor.fetchall()
    for row in results:
        print(f"  {row['最后付款时间']} ({row['cnt']}条)")

    # 检查买家昵称样本
    print("\n=== 买家昵称样本 ===")
    cursor.execute("""
        SELECT 买家昵称, MIN(最后付款时间) as min_time, MAX(最后付款时间) as max_time, COUNT(DISTINCT 订单号) as order_count
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 IS NOT NULL AND 买家昵称 != ''
        GROUP BY 买家昵称
        LIMIT 5
    """)
    results = cursor.fetchall()
    for row in results:
        print(f"  {row['买家昵称']}: min={row['min_time']}, max={row['max_time']}, orders={row['order_count']}")

conn.close()
