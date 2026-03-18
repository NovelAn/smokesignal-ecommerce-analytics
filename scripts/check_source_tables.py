"""
检查源表数据
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
    # 检查所有表
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print("=== 数据库中的表 ===")
    for t in tables:
        table_name = list(t.values())[0]
        print(f"  - {table_name}")

    # 检查源表数据量
    print("\n=== 源表数据量 ===")
    source_tables = [
        "dunhill_bi订单源",
        "dunhill_dtc订单源_hive",
        "dunhill_tm退款源",
        "dunhill_dtc退款源_hive"
    ]

    for table in source_tables:
        try:
            cursor.execute(f"SELECT COUNT(*) as cnt FROM `{table}`")
            cnt = cursor.fetchone()['cnt']
            print(f"  {table}: {cnt}条")
        except Exception as e:
            print(f"  {table}: 错误 - {e}")

    # 查看订单源表样本
    print("\n=== dunhill_bi订单源 样本 ===")
    try:
        cursor.execute("""
            SELECT 买家昵称, 订单号, 付款时间, 成交总金额 FROM dunhill_bi订单源
            WHERE 买家昵称 IS NOT NULL AND 买家昵称 != ''
            LIMIT 3
        """)
        for row in cursor.fetchall():
            print(f"  {row['买家昵称']} | {row['订单号']} | {row['付款时间']} | {row['成交总金额']}")
    except Exception as e:
        print(f"  错误: {e}")

    print("\n=== dunhill_dtc订单源_hive 样本 ===")
    try:
        cursor.execute("""
            SELECT 买家昵称, 订单号, 付款时间, 成交总金额 FROM dunhill_dtc订单源_hive
            WHERE 买家昵称 IS NOT NULL AND 买家昵称 != ''
            LIMIT 3
        """)
        for row in cursor.fetchall():
            print(f"  {row['买家昵称']} | {row['订单号']} | {row['付款时间']} | {row['成交总金额']}")
    except Exception as e:
        print(f"  错误: {e}")

    # 直接从源表统计买家
    print("\n=== 从源表统计唯一买家 ===")
    cursor.execute("""
        SELECT COUNT(DISTINCT 买家昵称) as cnt
        FROM dunhill_bi订单源
        WHERE 买家昵称 IS NOT NULL AND 买家昵称 != ''
    """)
    print(f"  dunhill_bi订单源: {cursor.fetchone()['cnt']}个唯一买家")

    cursor.execute("""
        SELECT COUNT(DISTINCT 买家昵称) as cnt
        FROM dunhill_dtc订单源_hive
        WHERE 买家昵称 IS NOT NULL AND 买家昵称 != ''
    """)
    print(f"  dunhill_dtc订单源_hive: {cursor.fetchone()['cnt']}个唯一买家")

conn.close()
