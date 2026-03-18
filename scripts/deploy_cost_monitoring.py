"""
Deploy Cost Monitoring Tables - 部署成本监控数据库表
运行此脚本以创建AI成本监控所需的数据库表
"""
import sys
import os
sys.path.insert(0, 'backend')

# Set UTF-8 encoding for Windows console
if os.name == 'nt':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from backend.database.db_config_manager import DBConfigManager
from backend.config import settings
import pymysql


def deploy_tables():
    """部署成本监控表"""
    print("="*60)
    print("部署AI成本监控数据库表")
    print("="*60)

    # 读取SQL脚本
    sql_file = "backend/database/sql/create_cost_monitoring_tables.sql"
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # 连接数据库
    try:
        db_configs = DBConfigManager.get_db_config_for_pymysql()
        db_name = settings.db_name_to_use if settings.db_name_to_use else "dunhill"
        db_config = None

        # 尝试精确匹配数据库配置
        for config in db_configs:
            if config["database"] == db_name:
                db_config = config
                break

        # 如果没找到，使用第一个配置（通常是唯一配置）
        if db_config is None and len(db_configs) > 0:
            print(f"[提示] 未找到数据库 '{db_name}'，使用第一个可用配置: {db_configs[0]['database']}")
            db_config = db_configs[0]

        if db_config is None:
            print(f"[错误] 未找到数据库配置: {db_name}")
            return False

        print(f"\n[连接] 连接到数据库: {db_name}")
        conn = pymysql.connect(**db_config)

        # 分割SQL语句（按分号分割）
        statements = []
        for statement in sql_content.split(';'):
            statement = statement.strip()
            if statement:
                statements.append(statement)

        print(f"[执行] 执行 {len(statements)} 条SQL语句...")

        with conn.cursor() as cursor:
            for i, statement in enumerate(statements, 1):
                try:
                    cursor.execute(statement)
                    print(f"  [{i}/{len(statements)}] OK")
                except Exception as e:
                    print(f"  [{i}/{len(statements)}] FAILED: {str(e)}")
                    # 继续执行其他语句

        conn.commit()
        print("\n[完成] 数据库表部署成功！")

        # 验证表是否创建成功
        with conn.cursor() as cursor:
            cursor.execute(
                "SHOW TABLES LIKE 'ai_cost%'"
            )
            tables = cursor.fetchall()

            print(f"\n[验证] 已创建的表:")
            for table in tables:
                table_name = list(table.values())[0]
                print(f"  - {table_name}")

        return True

    except Exception as e:
        print(f"\n[错误] 部署失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = deploy_tables()
    sys.exit(0 if success else 1)
