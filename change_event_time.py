"""
修改定时任务时间 - 从凌晨 2:00 改为上午 11:00
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

print("修改 buyer_summary 自动刷新时间")
print("=" * 60)
print("从：每天凌晨 2:00")
print("改为：每天上午 11:00\n")

conn = pymysql.connect(**DB_CONFIG)

try:
    with conn.cursor() as cursor:
        # 1. 检查当前事件
        print("1. 检查当前定时任务...")
        try:
            cursor.execute("SHOW EVENTS WHERE Name = 'event_refresh_buyer_summary'")
            event = cursor.fetchone()
            if event:
                print(f"   ✓ 找到定时任务: {event[1]}")
                print(f"   执行时间: {event[6]}")
            else:
                print("   ⚠️  未找到定时任务")
        except Exception as e:
            print(f"   ⚠️  查询失败: {e}")

        # 2. 删除旧事件
        print("\n2. 删除旧定时任务...")
        cursor.execute("DROP EVENT IF EXISTS event_refresh_buyer_summary")
        conn.commit()
        print("   ✓ 旧定时任务已删除")

        # 3. 创建新事件（上午 11:00）
        print("\n3. 创建新定时任务（上午 11:00）...")
        create_event_sql = """
        CREATE EVENT event_refresh_buyer_summary
        ON SCHEDULE EVERY 1 DAY
        STARTS CONCAT(CURDATE(), ' 11:00:00')
        COMMENT '每天上午11点刷新买家汇总表'
        DO CALL refresh_buyer_summary()
        """
        cursor.execute(create_event_sql)
        conn.commit()
        print("   ✓ 新定时任务创建成功")

        # 4. 验证新事件
        print("\n4. 验证新定时任务...")
        cursor.execute("SHOW EVENTS WHERE Name = 'event_refresh_buyer_summary'")
        event = cursor.fetchone()
        if event:
            print(f"   ✓ 事件名称: {event[1]}")
            print(f"   执行间隔: {event[4]}")
            print(f"   开始时间: {event[5]}")
            print(f"   最后执行时间: {event[6] or '尚未执行'}")
            print(f"   状态: {'启用' if event[7] == 'ENABLED' else '禁用'}")

        # 5. 检查事件调度器状态
        print("\n5. 检查事件调度器状态...")
        cursor.execute("SHOW VARIABLES LIKE 'event_scheduler'")
        status = cursor.fetchone()
        if status:
            scheduler_status = status[1]
            print(f"   事件调度器: {scheduler_status}")
            if scheduler_status == 'ON':
                print("   ✓ 事件调度器已启用")
            else:
                print("   ⚠️  事件调度器未启用，定时任务不会自动执行")
                print("   提示：请联系数据库管理员启用事件调度器")

    print("\n" + "=" * 60)
    print("✅ 定时任务修改完成！")
    print(" buyer_summary 表将从明天上午 11:00 开始自动刷新")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()

finally:
    conn.close()
