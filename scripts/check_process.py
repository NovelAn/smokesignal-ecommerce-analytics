#!/usr/bin/env python3
"""检查存储过程执行状态"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.db_config_manager import DBConfigManager
from backend.database import Database

# 加载配置
raw_db_configs = DBConfigManager.load_db_config()
db_name = raw_db_configs[1]['name']

print("🔍 检查数据库状态...")
db = Database(db_name=db_name)

# 检查表中数据
print("\n📊 当前数据状态:")
result = db.execute_query("SELECT COUNT(*) as total FROM target_buyers_precomputed")
print(f"   记录数: {result[0]['total']}")

# 检查updated_at时间
result = db.execute_query("""
    SELECT MAX(updated_at) as last_update,
           MIN(updated_at) as first_update
    FROM target_buyers_precomputed
""")
if result[0]['last_update']:
    print(f"   最后更新: {result[0]['last_update']}")
    print(f"   最早更新: {result[0]['first_update']}")
else:
    print("   没有更新时间记录")

# 检查是否有临时表存在
result = db.execute_query("SHOW TABLES LIKE 'tmp_target_buyers_new%'")
if result:
    print(f"\n⏳ 发现临时表: {len(result)} 个")
    for table in result:
        for key, value in table.items():
            print(f"   - {value}")
else:
    print("\n✅ 没有临时表 (说明过程已完成)")
