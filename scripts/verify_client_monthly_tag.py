#!/usr/bin/env python3
"""验证client_monthly_tag字段是否获取了最近购买记录的tag"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.db_config_manager import DBConfigManager
from backend.database import Database

# 加载配置
raw_db_configs = DBConfigManager.load_db_config()
db_name = raw_db_configs[1]['name']

print("🔍 验证client_monthly_tag逻辑...")
db = Database(db_name=db_name)

# 获取几个示例买家
print("\n1️⃣ 检查预计算表中的数据:")
result = db.execute_query("""
    SELECT buyer_nick, client_monthly_tag, last_purchase_date
    FROM target_buyers_precomputed
    LIMIT 5
""")

print("预计算表中的数据 (当前值):")
for row in result:
    print(f"   - {row['buyer_nick']}: {row['client_monthly_tag']} (最后购买: {row['last_purchase_date']})")

# 检查这些买家在原始表中最近购买记录的client_monthly_tag
print("\n2️⃣ 检查原始数据表中的最近记录:")
for row in result:
    buyer_nick = row['buyer_nick']
    result2 = db.execute_query("""
        SELECT
            买家昵称,
            client_monthly_tag,
            最后付款时间,
            订单号
        FROM dunhill_t01_trade_line
        WHERE 买家昵称 = %s
        ORDER BY 最后付款时间 DESC
        LIMIT 1
    """, (buyer_nick,))

    if result2:
        raw_row = result2[0]
        match = "✅" if raw_row['client_monthly_tag'] == row['client_monthly_tag'] else "❌"
        print(f"   {match} {raw_row['买家昵称']}: 原始={raw_row['client_monthly_tag']}, 预计算={row['client_monthly_tag']}")
        print(f"      最后购买时间: {raw_row['最后付款时间']}, 订单号: {raw_row['订单号']}")

# 统计新老客分布
print("\n3️⃣ 统计新老客分布:")
result = db.execute_query("""
    SELECT
        buyer_type,
        client_monthly_tag,
        COUNT(*) as count
    FROM target_buyers_precomputed
    GROUP BY buyer_type, client_monthly_tag
    ORDER BY buyer_type, client_monthly_tag
""")

print("买家类型 × 新老客 交叉统计:")
for row in result:
    print(f"   - {row['buyer_type']} × {row['client_monthly_tag']}: {row['count']}人")
