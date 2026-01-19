#!/usr/bin/env python3
"""
部署目标买家预计算表
自动执行SQL脚本并验证部署结果
"""
import sys
import os
import time

# 添加项目根目录到path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from backend.database.db_config_manager import DBConfigManager
from backend.database import Database

def read_sql_file(file_path: str) -> str:
    """读取SQL文件内容"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def execute_sql_script(db: Database, sql: str):
    """执行SQL脚本(按语句分割)"""
    # 移除SQL注释
    lines = []
    for line in sql.split('\n'):
        # 跳过注释行
        if line.strip().startswith('--'):
            continue
        lines.append(line)

    sql_cleaned = '\n'.join(lines)

    # 按分号分割语句
    statements = []
    current_statement = []

    for line in sql_cleaned.split('\n'):
        stripped = line.strip()
        if stripped:
            current_statement.append(line)
            if stripped.endswith(';'):
                statements.append('\n'.join(current_statement))
                current_statement = []

    # 执行每个语句
    for i, statement in enumerate(statements, 1):
        try:
            if statement.strip():
                print(f"执行语句 {i}/{len(statements)}...")
                db.execute_query(statement)
                print(f"✅ 语句 {i} 执行成功")
        except Exception as e:
            print(f"❌ 语句 {i} 执行失败: {e}")
            print(f"问题语句:\n{statement[:200]}")
            # 继续执行，不中断

def main():
    print("=" * 60)
    print("🚀 开始部署目标买家预计算表")
    print("=" * 60)

    # 1. 选择数据库
    print("\n📋 可用数据库:")

    # 加载配置
    from backend.database.db_config_manager import DBConfigManager

    # 加载pymysql格式的配置
    db_configs = DBConfigManager.get_db_config_for_pymysql()

    # 加载原始配置获取name字段
    raw_db_configs = DBConfigManager.load_db_config()

    for i, db_config in enumerate(raw_db_configs):
        print(f"  {i}. {db_config['database']} @ {db_config['host']}")

    # 使用第二个数据库(阿里云数据库)
    db_index = 1
    db_name = raw_db_configs[db_index]['name']  # 使用name字段: 'aliyunDB'

    print(f"\n✅ 使用数据库: {db_configs[db_index]['database']} @ {db_configs[db_index]['host']}")

    # 2. 连接数据库
    print("\n🔗 连接数据库...")
    db = Database(db_name=db_name)
    print("✅ 数据库连接成功")

    # 3. 读取SQL脚本
    sql_file = os.path.join(
        os.path.dirname(__file__),
        '..',
        'backend',
        'database',
        'sql',
        'create_target_buyers_precomputed.sql'
    )

    print(f"\n📄 读取SQL文件: {sql_file}")
    if not os.path.exists(sql_file):
        print(f"❌ SQL文件不存在: {sql_file}")
        return

    sql_content = read_sql_file(sql_file)
    print(f"✅ SQL文件读取成功 ({len(sql_content)} 字符)")

    # 4. 执行SQL脚本
    print("\n⚙️  开始执行SQL脚本...")
    print("-" * 60)

    start_time = time.time()
    execute_sql_script(db, sql_content)

    elapsed = time.time() - start_time
    print("-" * 60)
    print(f"✅ SQL脚本执行完成 (耗时: {elapsed:.2f}秒)")

    # 5. 验证部署
    print("\n🔍 验证部署结果...")
    print("-" * 60)

    try:
        # 检查表是否存在
        result = db.execute_query("SHOW TABLES LIKE 'target_buyers_precomputed'")
        if result:
            print("✅ 预计算表已创建")
        else:
            print("❌ 预计算表未找到")
            return

        # 检查数据量
        result = db.execute_query("SELECT COUNT(*) as total FROM target_buyers_precomputed")
        total = result[0]['total'] if result else 0
        print(f"✅ 目标买家总数: {total}")

        # 按类型统计
        result = db.execute_query("""
            SELECT buyer_type, COUNT(*) as count
            FROM target_buyers_precomputed
            GROUP BY buyer_type
        """)
        if result:
            print("✅ 买家类型分布:")
            for row in result:
                print(f"   - {row['buyer_type']}: {row['count']}")

        # 检查字段
        result = db.execute_query("DESCRIBE target_buyers_precomputed")
        print(f"✅ 表字段数量: {len(result)}")

        # 检查索引
        result = db.execute_query("SHOW INDEX FROM target_buyers_precomputed")
        print(f"✅ 索引数量: {len(result)}")

    except Exception as e:
        print(f"❌ 验证失败: {e}")

    print("-" * 60)

    # 6. 检查定时任务
    print("\n⏰ 检查定时任务...")
    try:
        result = db.execute_query("SHOW EVENTS LIKE 'event_refresh_target_buyers'")
        if result:
            print("✅ 定时任务已创建")
            event = result[0]
            print(f"   执行时间: 每天 {event['starts']}")
        else:
            print("⚠️  定时任务未找到，请手动创建")
    except Exception as e:
        print(f"⚠️  无法检查定时任务: {e}")

    # 7. 完成
    print("\n" + "=" * 60)
    print("🎉 部署完成!")
    print("=" * 60)
    print("\n📝 下一步:")
    print("1. 测试手动更新: CALL refresh_target_buyers_precomputed();")
    print("2. 启动后端服务: python -m uvicorn backend.main:app --reload")
    print("3. 测试新API: curl http://localhost:8000/api/v2/buyers?limit=10")
    print("\n")

if __name__ == "__main__":
    main()
