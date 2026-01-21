#!/usr/bin/env python3
"""检查数据库中的存储过程"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.db_config_manager import DBConfigManager
from backend.database import Database

# 加载配置
raw_db_configs = DBConfigManager.load_db_config()
db_name = raw_db_configs[1]['name']  # 使用aliyunDB

print("🔍 检查存储过程...")
db = Database(db_name=db_name)

# 检查存储过程
result = db.execute_query("SHOW PROCEDURE STATUS WHERE Db = 'dunhill'")
if result:
    print("\n✅ 已创建的存储过程:")
    for proc in result:
        print(f"   - {proc['Name']}")
else:
    print("\n❌ 没有找到存储过程")

# 检查事件调度器
result = db.execute_query("SHOW EVENTS LIKE 'event_refresh_target_buyers'")
if result:
    print("\n✅ 已创建的事件:")
    for event in result:
        print(f"   - {event['Name']}")
else:
    print("\n❌ 没有找到定时事件")
