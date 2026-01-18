"""
调试数据库数据
"""
import pymysql
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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
    # 检查总记录数
    cursor.execute("SELECT COUNT(*) as total FROM dunhill_t01_trade_line")
    print(f"总记录数: {cursor.fetchone()['total']}")

    # 检查有买家昵称的记录
    cursor.execute("SELECT COUNT(*) as cnt FROM dunhill_t01_trade_line WHERE 买家昵称 IS NOT NULL AND 买家昵称 != ''")
    print(f"有买家昵称的记录: {cursor.fetchone()['cnt']}")

    # 检查有效日期格式
    cursor.execute("""
        SELECT COUNT(*) as cnt
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 IS NOT NULL AND 买家昵称 != ''
          AND 最后付款时间 IS NOT NULL AND 最后付款时间 != ''
    """)
    print(f"有付款时间的记录: {cursor.fetchone()['cnt']}")

    # 查看日期格式样本
    cursor.execute("""
        SELECT 最后付款时间, COUNT(*) as cnt
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 IS NOT NULL AND 买家昵称 != ''
          AND 最后付款时间 IS NOT NULL
          AND 最后付款时间 != ''
        GROUP BY 最后付款时间
        ORDER BY cnt DESC
        LIMIT 10
    """)
    print("\n日期格式样本:")
    for row in cursor.fetchall():
        print(f"  {row['最后付款时间']} ({row['cnt']}条)")

    # 检查有多少唯一的买家
    cursor.execute("""
        SELECT COUNT(DISTINCT 买家昵称) as cnt
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 IS NOT NULL AND 买家昵称 != ''
    """)
    print(f"\n唯一买家数: {cursor.fetchone()['cnt']}")

    # 测试过滤后的数据
    cursor.execute("""
        SELECT COUNT(*) as cnt
        FROM (
            SELECT 买家昵称, 订单号, 最后付款时间
            FROM dunhill_t01_trade_line
            WHERE 买家昵称 IS NOT NULL AND 买家昵称 != ''
              AND 最后付款时间 IS NOT NULL AND 最后付款时间 != ''
              AND 最后付款时间 REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
        ) AS t
    """)
    print(f"过滤后有效记录: {cursor.fetchone()['cnt']}")

    # 查看实际样本
    cursor.execute("""
        SELECT 买家昵称, 最后付款时间, 订单号
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 IS NOT NULL AND 买家昵称 != ''
        LIMIT 5
    """)
    print("\n实际样本:")
    for row in cursor.fetchall():
        print(f"  {row['买家昵称']} | {row['最后付款时间']} | {row['订单号']}")

conn.close()
