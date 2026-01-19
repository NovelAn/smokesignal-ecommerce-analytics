"""
测试数据库连接
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from backend.config import settings
from backend.database import Database

print(f"Settings.db_name_to_use: {settings.db_name_to_use}")

db = Database(db_name=settings.db_name_to_use if settings.db_name_to_use else None)
print(f"Database config: {db.config['host']} / {db.config['database']}")

# 测试查询
result = db.execute_query("SHOW TABLES LIKE 'buyer_summary'")
print(f"Tables found: {result}")

if result:
    count = db.execute_query("SELECT COUNT(*) as cnt FROM buyer_summary")
    print(f"buyer_summary count: {count}")
else:
    print("WARNING: buyer_summary table not found in this database!")

# 列出所有表
tables = db.execute_query("SHOW TABLES")
print(f"\nAll tables in database ({len(tables)}):")
for t in tables[:10]:
    print(f"  - {list(t.values())[0]}")
