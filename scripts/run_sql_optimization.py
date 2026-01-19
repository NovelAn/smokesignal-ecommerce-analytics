"""
执行 buyer_summary 表优化脚本
连接到 Aliyun 数据库并执行 SQL
"""
import pymysql
import time
import sys
import io

# 设置标准输出编码为 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 数据库配置
DB_CONFIG = {
    "host": "rm-uf68p191h7j2o40s34o.mysql.rds.aliyuncs.com",
    "user": "novelan",
    "password": "Anna069832-",
    "database": "dunhill",
    "port": 3306,
    "charset": "utf8mb4"
}

def execute_sql(conn, sql, description):
    """执行 SQL 语句"""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    try:
        with conn.cursor() as cursor:
            for statement in sql.split(';'):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)
            conn.commit()
        print(f"✅ {description} - 成功")
        return True
    except Exception as e:
        print(f"❌ {description} - 失败: {e}")
        conn.rollback()
        return False

def main():
    print("🚀 开始执行 buyer_summary 表优化...")
    print(f"📍 数据库: {DB_CONFIG['host']}/{DB_CONFIG['database']}")

    # 连接数据库
    try:
        conn = pymysql.connect(**DB_CONFIG)
        print(f"✅ 数据库连接成功")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        sys.exit(1)

    try:
        # 步骤1: 创建索引（MySQL 不支持 IF NOT EXISTS，使用 TRY-CATCH）
        print(f"\n{'='*60}")
        print(f"🔄 步骤1: 创建基础表索引")
        print(f"{'='*60}")

        indexes = [
            ("idx_bi_buyer_nick", "CREATE INDEX idx_bi_buyer_nick ON dunhill_bi订单源(买家昵称)"),
            ("idx_bi_payment_time", "CREATE INDEX idx_bi_payment_time ON dunhill_bi订单源(付款时间)"),
            ("idx_bi_order_id", "CREATE INDEX idx_bi_order_id ON dunhill_bi订单源(订单号)"),
            ("idx_bi_nick_time", "CREATE INDEX idx_bi_nick_time ON dunhill_bi订单源(买家昵称, 付款时间)"),
            ("idx_dtc_buyer_nick", "CREATE INDEX idx_dtc_buyer_nick ON dunhill_dtc订单源_hive(买家昵称)"),
            ("idx_dtc_payment_time", "CREATE INDEX idx_dtc_payment_time ON dunhill_dtc订单源_hive(付款时间)"),
            ("idx_dtc_order_id", "CREATE INDEX idx_dtc_order_id ON dunhill_dtc订单源_hive(订单号)"),
            ("idx_dtc_nick_time", "CREATE INDEX idx_dtc_nick_time ON dunhill_dtc订单源_hive(买家昵称, 付款时间)"),
        ]

        for name, sql in indexes:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql)
                conn.commit()
                print(f"   ✅ {name}")
            except pymysql.err.OperationalError as e:
                if e.args[0] == 1061:  # Duplicate key name
                    print(f"   ⏭️  {name} (已存在)")
                else:
                    print(f"   ⚠️  {name}: {e}")
            except Exception as e:
                print(f"   ⚠️  {name}: {e}")

        # 步骤2: 创建 buyer_summary 表
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS buyer_summary (
            buyer_nick VARCHAR(255) PRIMARY KEY,
            first_order_date DATETIME,
            last_order_date DATETIME,
            total_orders INT,
            total_gmv DECIMAL(18, 2),
            total_refund DECIMAL(18, 2),
            city VARCHAR(100),
            last_client_monthly_tag VARCHAR(50),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_last_order (last_order_date),
            INDEX idx_city (city)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='买家汇总表，每天凌晨2点自动更新';
        """
        execute_sql(conn, create_table_sql, "步骤2: 创建 buyer_summary 表")

        # 步骤3: 清空旧数据并导入新数据
        print(f"\n{'='*60}")
        print(f"🔄 步骤3: 导入初始数据（这可能需要 5-15 分钟，请耐心等待...）")
        print(f"{'='*60}")

        # 先清空
        try:
            with conn.cursor() as cursor:
                cursor.execute("TRUNCATE TABLE buyer_summary")
            conn.commit()
            print("✅ 清空旧数据完成")
        except:
            pass

        # 导入数据 - 直接从源表（因为视图数据有问题）
        start_time = time.time()
        print(f"   正在从源表导入数据...")

        # 先从 bi 订单源导入
        insert_sql_bi = """
        INSERT INTO buyer_summary (
            buyer_nick, first_order_date, last_order_date, total_orders,
            total_gmv, total_refund, city, last_client_monthly_tag
        )
        SELECT
            买家昵称 as buyer_nick,
            MIN(付款时间) as first_order_date,
            MAX(付款时间) as last_order_date,
            COUNT(DISTINCT 订单号) as total_orders,
            SUM(成交总金额) as total_gmv,
            0 as total_refund,
            MAX(城市) as city,
            MAX(client_monthly_tag) as last_client_monthly_tag
        FROM dunhill_bi订单源
        WHERE 买家昵称 IS NOT NULL
          AND 买家昵称 != ''
          AND 付款时间 IS NOT NULL
        GROUP BY 买家昵称
        """

        # 再从 dtc 订单源导入（使用 INSERT IGNORE 避免重复）
        insert_sql_dtc = """
        INSERT IGNORE INTO buyer_summary (
            buyer_nick, first_order_date, last_order_date, total_orders,
            total_gmv, total_refund, city, last_client_monthly_tag
        )
        SELECT
            买家昵称 as buyer_nick,
            MIN(付款时间) as first_order_date,
            MAX(付款时间) as last_order_date,
            COUNT(DISTINCT 订单号) as total_orders,
            SUM(成交总金额) as total_gmv,
            0 as total_refund,
            MAX(城市) as city,
            MAX(client_monthly_tag) as last_client_monthly_tag
        FROM dunhill_dtc订单源_hive
        WHERE 买家昵称 IS NOT NULL
          AND 买家昵称 != ''
          AND 付款时间 IS NOT NULL
        GROUP BY 买家昵称
        """

        try:
            affected_rows = 0

            # 导入 bi 数据
            with conn.cursor() as cursor:
                cursor.execute(insert_sql_bi)
                affected_rows += cursor.rowcount
            conn.commit()
            print(f"   ✅ dunhill_bi订单源: {cursor.rowcount}条")

            # 导入 dtc 数据
            with conn.cursor() as cursor:
                cursor.execute(insert_sql_dtc)
                affected_rows += cursor.rowcount
            conn.commit()
            print(f"   ✅ dunhill_dtc订单源_hive: {cursor.rowcount}条")

            elapsed = time.time() - start_time
            print(f"✅ 数据导入完成！")
            print(f"   - 总导入记录数: {affected_rows}")
            print(f"   - 耗时: {elapsed:.1f} 秒")
        except Exception as e:
            print(f"❌ 数据导入失败: {e}")
            import traceback
            traceback.print_exc()

        # 验证数据
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM buyer_summary")
            count = cursor.fetchone()[0]
            print(f"   - 当前买家总数: {count}")

        # 步骤4: 创建存储过程（使用 pymysql 的多语句执行）
        print(f"\n{'='*60}")
        print(f"🔄 步骤4: 创建存储过程")
        print(f"{'='*60}")

        # 删除旧存储过程
        try:
            with conn.cursor() as cursor:
                cursor.execute("DROP PROCEDURE IF EXISTS refresh_buyer_summary")
            conn.commit()
            print("✅ 删除旧存储过程完成")
        except:
            pass

        # 创建新存储过程
        create_procedure_sql = """
        CREATE PROCEDURE refresh_buyer_summary()
        BEGIN
            DECLARE start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            DECLARE affected_rows INT DEFAULT 0;

            SELECT CONCAT('开始刷新买家汇总表: ', start_time) AS message;

            -- 先清空汇总表
            TRUNCATE TABLE buyer_summary;

            -- 从 bi 订单源导入
            INSERT INTO buyer_summary (
                buyer_nick, first_order_date, last_order_date, total_orders,
                total_gmv, total_refund, city, last_client_monthly_tag
            )
            SELECT
                买家昵称 as buyer_nick,
                MIN(付款时间) as first_order_date,
                MAX(付款时间) as last_order_date,
                COUNT(DISTINCT 订单号) as total_orders,
                SUM(成交总金额) as total_gmv,
                0 as total_refund,
                MAX(城市) as city,
                MAX(client_monthly_tag) as last_client_monthly_tag
            FROM dunhill_bi订单源
            WHERE 买家昵称 IS NOT NULL AND 买家昵称 != '' AND 付款时间 IS NOT NULL
            GROUP BY 买家昵称;

            SET affected_rows = ROW_COUNT();

            -- 从 dtc 订单源导入（忽略重复）
            INSERT IGNORE INTO buyer_summary (
                buyer_nick, first_order_date, last_order_date, total_orders,
                total_gmv, total_refund, city, last_client_monthly_tag
            )
            SELECT
                买家昵称 as buyer_nick,
                MIN(付款时间) as first_order_date,
                MAX(付款时间) as last_order_date,
                COUNT(DISTINCT 订单号) as total_orders,
                SUM(成交总金额) as total_gmv,
                0 as total_refund,
                MAX(城市) as city,
                MAX(client_monthly_tag) as last_client_monthly_tag
            FROM dunhill_dtc订单源_hive
            WHERE 买家昵称 IS NOT NULL AND 买家昵称 != '' AND 付款时间 IS NOT NULL
            GROUP BY 买家昵称;

            SET affected_rows = affected_rows + ROW_COUNT();

            SELECT CONCAT('✅ 刷新完成！更新/插入了 ', affected_rows, ' 条记录') AS message;
            SELECT CONCAT('耗时: ', TIMESTAMPDIFF(SECOND, start_time, CURRENT_TIMESTAMP), ' 秒') AS duration;
            SELECT CONCAT('当前买家总数: ', (SELECT COUNT(*) FROM buyer_summary)) AS total_buyers;
        END
        """
        try:
            with conn.cursor() as cursor:
                cursor.execute(create_procedure_sql)
            conn.commit()
            print("✅ 存储过程创建成功")
        except Exception as e:
            print(f"❌ 存储过程创建失败: {e}")

        # 步骤5: 创建定时事件
        print(f"\n{'='*60}")
        print(f"🔄 步骤5: 创建定时任务（每天凌晨2点）")
        print(f"{'='*60}")

        # 启用事件调度器
        try:
            with conn.cursor() as cursor:
                cursor.execute("SET GLOBAL event_scheduler = ON")
            conn.commit()
            print("✅ 事件调度器已启用")
        except Exception as e:
            print(f"⚠️  启用事件调度器失败（可能需要SUPER权限）: {e}")

        # 创建事件
        try:
            with conn.cursor() as cursor:
                cursor.execute("DROP EVENT IF EXISTS event_refresh_buyer_summary")
                cursor.execute("""
                    CREATE EVENT event_refresh_buyer_summary
                    ON SCHEDULE EVERY 1 DAY
                    STARTS CONCAT(CURDATE() + INTERVAL 1 DAY, ' 02:00:00')
                    COMMENT '每天凌晨2点刷新买家汇总表'
                    DO CALL refresh_buyer_summary()
                """)
            conn.commit()
            print("✅ 定时任务创建成功")
        except Exception as e:
            print(f"⚠️  定时任务创建失败（可能需要 SUPER 权限）: {e}")

        # 步骤6: 创建辅助视图
        create_view_sql = """
        CREATE OR REPLACE VIEW v_buyer_list AS
        SELECT
            buyer_nick, first_order_date, last_order_date, total_orders,
            total_gmv, total_refund, (total_gmv - total_refund) as net_sales,
            city, last_client_monthly_tag, updated_at
        FROM buyer_summary
        ORDER BY last_order_date DESC;
        """
        execute_sql(conn, create_view_sql, "步骤6: 创建辅助视图")

        # 验证结果
        print(f"\n{'='*60}")
        print(f"📊 验证结果")
        print(f"{'='*60}")

        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # 检查表
            cursor.execute("SHOW TABLES LIKE 'buyer_summary'")
            table_exists = cursor.fetchone()
            print(f"✅ buyer_summary 表存在: {bool(table_exists)}")

            # 检查数据
            cursor.execute("SELECT COUNT(*) as cnt FROM buyer_summary")
            count = cursor.fetchone()['cnt']
            print(f"✅ 买家总数: {count}")

            # 检查存储过程
            cursor.execute("SHOW PROCEDURE STATUS WHERE Name = 'refresh_buyer_summary'")
            proc_exists = cursor.fetchone()
            print(f"✅ 存储过程存在: {bool(proc_exists)}")

            # 检查事件
            try:
                cursor.execute("SHOW EVENTS WHERE Name = 'event_refresh_buyer_summary'")
                event_exists = cursor.fetchone()
                print(f"✅ 定时任务存在: {bool(event_exists)}")
            except Exception as e:
                print(f"⚠️  定时任务检查失败（可能需要权限）: {e}")

            # 样例数据
            cursor.execute("SELECT * FROM buyer_summary LIMIT 3")
            samples = cursor.fetchall()
            print(f"\n📋 样例数据（前3条）:")
            for row in samples:
                print(f"   - {row['buyer_nick']}: {row['total_orders']}单, ¥{row['total_gmv']:.2f}")

        print(f"\n{'='*60}")
        print(f"🎉 优化脚本执行完成！")
        print(f"{'='*60}")
        print(f"\n下一步:")
        print(f"1. 重启后端服务: python -m backend.main")
        print(f"2. 测试 API: http://localhost:8000/api/buyers")
        print(f"3. 手动刷新汇总表: CALL refresh_buyer_summary();")

    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
        print(f"\n数据库连接已关闭")

if __name__ == "__main__":
    main()
