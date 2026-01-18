"""
更新存储过程 - 使用修复后的视图获取退款数据
"""
import pymysql
import pymysql.err
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

print("更新存储过程 refresh_buyer_summary()...")
print("使用修复后的视图获取退款数据\n")

conn = pymysql.connect(**DB_CONFIG)

try:
    with conn.cursor() as cursor:
        # 删除旧存储过程
        print("1. 删除旧存储过程...")
        cursor.execute("DROP PROCEDURE IF EXISTS refresh_buyer_summary")
        conn.commit()
        print("   ✓ 旧存储过程已删除")

        # 创建新存储过程（不使用 DELIMITER）
        print("\n2. 创建新存储过程（包含退款数据）...")
        create_proc_sql = """
        CREATE PROCEDURE refresh_buyer_summary()
        BEGIN
            DECLARE start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            DECLARE affected_rows INT DEFAULT 0;

            SELECT CONCAT('开始刷新买家汇总表: ', start_time) AS message;

            TRUNCATE TABLE buyer_summary;

            INSERT INTO buyer_summary (
                buyer_nick, first_order_date, last_order_date, total_orders,
                total_gmv, total_refund, city, last_client_monthly_tag
            )
            SELECT
                买家昵称 as buyer_nick,
                MIN(最后付款时间) as first_order_date,
                MAX(最后付款时间) as last_order_date,
                COUNT(DISTINCT 订单号) as total_orders,
                SUM(成交总金额) as total_gmv,
                SUM(IFNULL(退款金额, 0)) as total_refund,
                MAX(城市) as city,
                MAX(client_monthly_tag) as last_client_monthly_tag
            FROM dunhill_t01_trade_line
            WHERE 买家昵称 IS NOT NULL AND 买家昵称 != '' AND 最后付款时间 IS NOT NULL
            GROUP BY 买家昵称;

            SET affected_rows = ROW_COUNT();

            SELECT CONCAT('✅ 刷新完成！更新了 ', affected_rows, ' 条记录') AS message;
            SELECT CONCAT('耗时: ', TIMESTAMPDIFF(SECOND, start_time, CURRENT_TIMESTAMP), ' 秒') AS duration;
            SELECT CONCAT('当前买家总数: ', (SELECT COUNT(*) FROM buyer_summary)) AS total_buyers;
            SELECT CONCAT('有退款记录的买家: ', (SELECT COUNT(*) FROM buyer_summary WHERE total_refund > 0)) AS refund_buyers;
        END
        """
        cursor.execute(create_proc_sql)
        conn.commit()
        print("   ✓ 新存储过程创建成功")

        # 执行存储过程刷新数据
        print("\n3. 执行存储过程刷新 buyer_summary 表...")
        cursor.execute("CALL refresh_buyer_summary()")

        # 存储过程返回多个结果集
        result_sets = []
        while True:
            try:
                result = cursor.fetchall()
                result_sets.append(result)
                if not cursor.nextset():
                    break
            except pymysql.err.Error:
                break

        # 显示输出消息
        for result_set in result_sets:
            for row in result_set:
                if isinstance(row, dict):
                    for key, value in row.items():
                        print(f"   {value}")
                elif isinstance(row, tuple) and len(row) > 0:
                    print(f"   {row[0]}")

        conn.commit()

        # 验证结果
        print("\n4. 验证数据...")
        with conn.cursor(pymysql.cursors.DictCursor) as cursor2:
            # 总记录数
            cursor2.execute("SELECT COUNT(*) as cnt FROM buyer_summary")
            total = cursor2.fetchone()['cnt']
            print(f"   ✓ 总买家数: {total}")

            # 有退款记录的买家
            cursor2.execute("SELECT COUNT(*) as cnt FROM buyer_summary WHERE total_refund > 0")
            refund_count = cursor2.fetchone()['cnt']
            print(f"   ✓ 有退款记录的买家: {refund_count}")

            # 退款金额统计
            cursor2.execute("SELECT SUM(total_refund) as sum FROM buyer_summary")
            refund_sum = cursor2.fetchone()['sum'] or 0
            print(f"   ✓ 总退款金额: {refund_sum:.2f}")

            # 样例数据（有退款的买家）
            cursor2.execute("""
                SELECT buyer_nick, total_orders, total_gmv, total_refund,
                       (total_gmv - total_refund) as net_sales
                FROM buyer_summary
                WHERE total_refund > 0
                ORDER BY total_refund DESC
                LIMIT 5
            """)
            samples = cursor2.fetchall()
            print(f"\n   退款最多的 5 个买家:")
            for row in samples:
                print(f"     {row['buyer_nick']}: {row['total_orders']}单, "
                      f"GMV={row['total_gmv']:.2f}, "
                      f"退款={row['total_refund']:.2f}, "
                      f"净销售额={row['net_sales']:.2f}")

    print("\n" + "=" * 60)
    print("✅ 存储过程更新完成！buyer_summary 表已刷新")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()

finally:
    conn.close()
