#!/usr/bin/env python3
"""测试手动刷新存储过程"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.db_config_manager import DBConfigManager
from backend.database import Database

# 加载配置
raw_db_configs = DBConfigManager.load_db_config()
db_name = raw_db_configs[1]['name']  # 使用aliyunDB

print("🔍 连接到阿里云数据库...")
db = Database(db_name=db_name)

# 检查当前数据量
print("\n📊 刷新前数据量...")
result = db.execute_query("SELECT COUNT(*) as total FROM target_buyers_precomputed")
before_count = result[0]['total']
print(f"   当前记录数: {before_count}")

# 按类型统计
print("\n   按类型分布:")
result = db.execute_query("""
    SELECT buyer_type, COUNT(*) as count
    FROM target_buyers_precomputed
    GROUP BY buyer_type
""")
for row in result:
    print(f"   - {row['buyer_type']}: {row['count']}")

# 执行存储过程
print("\n🚀 执行存储过程: CALL refresh_target_buyers_precomputed()")
print("="*60)

start_time = time.time()

try:
    result = db.execute_query("CALL refresh_target_buyers_precomputed()")

    elapsed = time.time() - start_time

    print(f"\n✅ 存储过程执行完成! (耗时: {elapsed:.2f}秒)")

    # 检查更新后的数据量
    print("\n📊 刷新后数据量...")
    result = db.execute_query("SELECT COUNT(*) as total FROM target_buyers_precomputed")
    after_count = result[0]['total']
    print(f"   当前记录数: {after_count}")

    if after_count != before_count:
        print(f"   📈 变化: {after_count - before_count:+d} 条记录")

    # 按类型统计
    print("\n   按类型分布:")
    result = db.execute_query("""
        SELECT buyer_type, COUNT(*) as count
        FROM target_buyers_precomputed
        GROUP BY buyer_type
    """)
    for row in result:
        print(f"   - {row['buyer_type']}: {row['count']}")

    # 检查最后更新时间
    print("\n⏰ 检查更新时间...")
    result = db.execute_query("SELECT NOW() as current_time")
    print(f"   当前时间: {result[0]['current_time']}")

    # 查看几条示例数据
    print("\n📋 数据示例(前3条)...")
    result = db.execute_query("""
        SELECT buyer_nick, buyer_type, vip_level, client_monthly_tag,
               historical_net_sales, l6m_spend
        FROM target_buyers_precomputed
        LIMIT 3
    """)
    for row in result:
        print(f"   - {row['buyer_nick']} | {row['buyer_type']} | {row['vip_level']} | "
              f"{row['client_monthly_tag']} | ¥{row['historical_net_sales']:.2f}")

    print("\n✅ 测试完成! 存储过程运行正常")

except Exception as e:
    print(f"\n❌ 存储过程执行失败: {e}")
    import traceback
    traceback.print_exc()
