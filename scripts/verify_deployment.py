#!/usr/bin/env python3
"""验证部署结果"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.db_config_manager import DBConfigManager
from backend.database import Database

# 加载配置
raw_db_configs = DBConfigManager.load_db_config()
db_name = raw_db_configs[1]['name']  # 使用aliyunDB

print("🔍 连接到阿里云数据库...")
db = Database(db_name=db_name)

# 1. 检查表是否存在
print("\n1️⃣ 检查预计算表...")
result = db.execute_query("SHOW TABLES LIKE 'target_buyers_precomputed'")
if result:
    print("✅ 表已创建")
else:
    print("❌ 表不存在")
    sys.exit(1)

# 2. 检查数据量
print("\n2️⃣ 检查数据量...")
result = db.execute_query("SELECT COUNT(*) as total FROM target_buyers_precomputed")
total = result[0]['total']
print(f"✅ 目标买家总数: {total}")

if total == 0:
    print("\n⚠️  数据为0！需要手动执行存储过程初始化数据")
    print("\n请在MySQL中执行:")
    print("mysql -h rm-uf68p191h7j2o40s34o.mysql.rds.aliyuncs.com -u novelan -p'Anna069832-' dunhill < backend/database/sql/create_target_buyers_precomputed.sql")
    print("\n或者手动调用:")
    print("CALL refresh_target_buyers_precomputed();")
else:
    # 3. 按类型统计
    print("\n3️⃣ 按类型统计...")
    result = db.execute_query("""
        SELECT buyer_type, COUNT(*) as count
        FROM target_buyers_precomputed
        GROUP BY buyer_type
    """)
    if result:
        print("买家类型分布:")
        for row in result:
            print(f"   - {row['buyer_type']}: {row['count']}")

    # 4. 查看数据示例
    print("\n4️⃣ 数据示例(前5条)...")
    result = db.execute_query("""
        SELECT buyer_nick, buyer_type, vip_level, client_monthly_tag,
               historical_net_sales, l6m_spend
        FROM target_buyers_precomputed
        LIMIT 5
    """)
    for row in result:
        print(f"   - {row['buyer_nick']} | {row['buyer_type']} | {row['vip_level']} | {row['client_monthly_tag']} | ¥{row['historical_net_sales']}")

print("\n✅ 验证完成!")
