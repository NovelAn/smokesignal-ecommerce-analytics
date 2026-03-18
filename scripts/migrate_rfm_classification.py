#!/usr/bin/env python3
"""
RFM Classification Migration Script
============================================
自动执行 RFM 分类迁移的 Python 脚本

Usage:
    python scripts/migrate_rfm_classification.py
"""

import os
import sys
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.db_config import DBConfigManager


def load_db_config():
    """加载数据库配置"""
    config_path = Path.home / "database_config.json"
    if not config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)
    return None


def get_connection(db_config, db_name=None):
    """获取数据库连接"""
    import pymysql

    config = db_config.get(db_name) if db_name else db_config.get("aliyunDB")
    if not config:
        raise ValueError(f"数据库配置 '{db_name}' 不存在")

    return pymysql.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        database=config["database"],
        charset='utf8mb4'
        cursorclass=pymysql.cursors.DictCursor
    )


def execute_sql_file(conn, sql_file_path, description=""):
    """执行 SQL 文件"""
    print(f"\n📄 执行: {description or sql_file_path}")
    print("-" * 50)

    with open(sql_file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # 移除注释行并分割成单独语句
    lines = []
    for line in sql_content.split('\n'):
        line = line.strip()
        if line and not line.startswith('--') and not line.startswith('/*'):
            lines.append(line)

    # 合并成完整语句
    full_sql = '\n'.join(lines)

    try:
        with conn.cursor() as cursor:
            # 处理多个语句
            statements = full_sql.split(';')

            for statement in statements:
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)

        affected = cursor.rowcount
        print(f"✅ 成功执行 ({affected} 行受影响)")
        return True

    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return False


def migrate_rfm_fields(conn):
    """迁移 RFM 字段"""
    print("\n" + "=" * 50)
    print("Phase 1: 检查并添加 RFM 字段")
    print("-" * 50)

    # 检查表是否存在
    with conn.cursor() as cursor:
        cursor.execute("SHOW TABLES LIKE 'target_buyers_precomputed'")
        result = cursor.fetchone()

        if not result:
            print("❌ 表 target_buyers_precomputed 不存在!")
            return False

    # 检查字段是否存在
    rfm_fields = [
        ('rfm_recency_score', 'INT DEFAULT 0 COMMENT "R分数(1-5): 最近购买时间"'),
        ('rfm_frequency_score', 'INT DEFAULT 0 COMMENT "F分数(1-5): 购买频次"'),
        ('rfm_monetary_score', 'INT DEFAULT 0 COMMENT "M分数(1-5): 消费金额"'),
        ('rfm_segment', 'VARCHAR(50) COMMENT "RFM客户分类"'),
        ('follow_priority', 'VARCHAR(10) COMMENT "跟进优先级: 紧急/高/中/低"'),
    ]

    for field_name, field_type in rfm_fields:
        with conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT COLUMN_NAME, DATA_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'target_buyers_precomputed'
                  AND COLUMN_NAME = '{field_name}'
            """)
            result = cursor.fetchone()

            if result:
                print(f"  ✓ 字段 {field_name} 已存在 ({result['COLUMN_NAME']})")
            else:
                # 添加字段
                print(f"  ➕ 添加字段 {field_name}...")
                try:
                    cursor.execute(f"ALTER TABLE target_buyers_precomputed ADD COLUMN {field_name} {field_type}")
                    print(f"  ✅ 添加成功")
                except Exception as e:
                    if "Duplicate" in str(e):
                        print(f"  ✓ 字段 {field_name} 已存在")
                    else:
                        print(f"  ❌ 添加失败: {e}")
                        return False

    return True


def calculate_rfm_scores(conn):
    """计算 RFM 分数"""
    print("\n" + "=" * 50)
    print("Phase 2: 计算 RFM 分数")
    print("-" * 50)

    # R 分数 (Recency - 最近购买时间)
    print("  计算 R 分数...")
    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE target_buyers_precomputed
            SET rfm_recency_score = CASE
                WHEN last_purchase_date IS NULL THEN 0
                WHEN DATEDIFF(NOW(), last_purchase_date) <= 60 THEN 5
                WHEN DATEDIFF(NOW(), last_purchase_date) <= 180 THEN 4
                WHEN DATEDIFF(NOW(), last_purchase_date) <= 365 THEN 3
                WHEN DATEDIFF(NOW(), last_purchase_date) <= 730 THEN 2
                ELSE 1
            END
        """)
        r_updated = cursor.rowcount
        print(f"  ✅ R 分数计算完成 ({r_updated} 条记录)")

    # F 分数(Frequency - 购买频次)
    print("  计算 F 分数...")
    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE target_buyers_precomputed
            SET rfm_frequency_score = CASE
                WHEN total_orders >= 5 THEN 5
                WHEN total_orders >= 3 THEN 4
                WHEN total_orders = 2 THEN 3
                WHEN total_orders = 1 AND chat_frequency_days > 0 THEN 2
                WHEN total_orders = 1 THEN 1
                ELSE 0
            END
        """)
        f_updated = cursor.rowcount
        print(f"  ✅ F 分数计算完成 ({f_updated} 条记录)")

    # M 分数(Monetary - 消费金额)
    print("  计算 M 分数...")
    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE target_buyers_precomputed
            SET rfm_monetary_score = CASE
                WHEN historical_net_sales >= 50000 THEN 5
                WHEN historical_net_sales >= 20000 THEN 4
                WHEN historical_net_sales >= 10000 THEN 3
                WHEN historical_net_sales >= 5000 THEN 2
                ELSE 1
            END
        """)
        m_updated = cursor.rowcount
        print(f"  ✅ M 分数计算完成 ({m_updated} 条记录)")


def determine_rfm_segments(conn):
    """确定 RFM 客户分类"""
    print("\n" + "=" * 50)
    print("Phase 3: 确定 RFM 客户分类 (覆盖125种组合)")
    print("-" * 50)

    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE target_buyers_precomputed
            SET rfm_segment = CASE
                -- M=5 (≥50K) - 核心VIP客户群
                WHEN rfm_monetary_score = 5 AND rfm_recency_score >= 4 AND rfm_frequency_score >= 4
                    THEN '重要价值客户'
                WHEN rfm_monetary_score = 5 AND rfm_recency_score >= 4 AND rfm_frequency_score <= 3
                    THEN '重要发展客户'
                WHEN rfm_monetary_score = 5 AND rfm_recency_score <= 3 AND rfm_frequency_score >= 4
                    THEN '重要保持客户'
                WHEN rfm_monetary_score = 5 AND rfm_recency_score <= 3 AND rfm_frequency_score <= 3
                    THEN '重要挽留客户'

                -- M=4 (20K-50K) - 高价值客户群
                WHEN rfm_monetary_score = 4 AND rfm_recency_score >= 4 AND rfm_frequency_score >= 4
                    THEN '优质活跃客户'
                WHEN rfm_monetary_score = 4 AND rfm_recency_score >= 4 AND rfm_frequency_score = 3
                    THEN '优质发展客户'
                WHEN rfm_monetary_score = 4 AND rfm_recency_score >= 4 AND rfm_frequency_score <= 2
                    THEN '优质新客'
                WHEN rfm_monetary_score = 4 AND rfm_recency_score <= 3 AND rfm_frequency_score >= 3
                    THEN '优质保持客户'
                WHEN rfm_monetary_score = 4 AND rfm_recency_score <= 3 AND rfm_frequency_score <= 2
                    THEN '优质挽留客户'

                -- M=3 (10K-20K) - 中等价值客户群
                WHEN rfm_monetary_score = 3 AND rfm_recency_score >= 4 AND rfm_frequency_score >= 4
                    THEN '成长活跃客户'
                WHEN rfm_monetary_score = 3 AND rfm_recency_score >= 4 AND rfm_frequency_score = 3
                    THEN '成长发展客户'
                WHEN rfm_monetary_score = 3 AND rfm_recency_score >= 4 AND rfm_frequency_score <= 2
                    THEN '成长新客'
                WHEN rfm_monetary_score = 3 AND rfm_recency_score <= 3 AND rfm_frequency_score >= 3
                    THEN '成长保持客户'
                WHEN rfm_monetary_score = 3 AND rfm_recency_score <= 3 AND rfm_frequency_score <= 2
                    THEN '成长挽留客户'

                -- M=2 (5K-10K) - 潜力客户群
                WHEN rfm_monetary_score = 2 AND rfm_recency_score >= 4 AND rfm_frequency_score >= 4
                    THEN '潜力活跃客户'
                WHEN rfm_monetary_score = 2 AND rfm_recency_score >= 4 AND rfm_frequency_score = 3
                    THEN '潜力发展客户'
                WHEN rfm_monetary_score = 2 AND rfm_recency_score >= 4 AND rfm_frequency_score <= 2
                    THEN '潜力新客'
                WHEN rfm_monetary_score = 2 AND rfm_recency_score <= 3 AND rfm_frequency_score >= 3
                    THEN '潜力保持客户'
                WHEN rfm_monetary_score = 2 AND rfm_recency_score <= 3 AND rfm_frequency_score <= 2
                    THEN '潜力挽留客户'

                -- M=1 (<5K) - 入门客户群
                WHEN rfm_monetary_score = 1 AND rfm_recency_score >= 4
                    THEN '新客培育'
                WHEN rfm_monetary_score = 1 AND rfm_recency_score IN (2, 3) AND rfm_frequency_score >= 3
                    THEN '低价值保持'
                WHEN rfm_monetary_score = 1 AND rfm_recency_score IN (2, 3) AND rfm_frequency_score <= 2
                    THEN '低价值挽留'

                -- 特殊情况
                WHEN rfm_recency_score = 1
                    THEN '已流失'
                WHEN rfm_recency_score = 0
                    THEN '无购买记录'

                ELSE '待分类'
            END
        """)
        s_updated = cursor.rowcount
        print(f"  ✅ RFM 分类完成 ({s_updated} 条记录)")


def calculate_follow_priority(conn):
    """计算跟进优先级"""
    print("\n" + "=" * 50)
    print("Phase 4: 计算跟进优先级")
    print("-" * 50)

    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE target_buyers_precomputed
            SET follow_priority = CASE
                -- 紧急: 核心VIP + 流失预警
                WHEN rfm_segment IN ('重要价值客户', '重要挽留客户', '重要保持客户') THEN '紧急'
                -- 高: 高价值客户群
                WHEN rfm_segment IN ('重要发展客户', '优质活跃客户', '优质发展客户', '优质新客', '优质保持客户', '优质挽留客户') THEN '高'
                -- 中: 中等价值客户群
                WHEN rfm_segment IN ('成长活跃客户', '成长发展客户', '成长新客', '成长保持客户', '成长挽留客户', '潜力活跃客户', '潜力发展客户', '潜力新客', '潜力保持客户') THEN '中'
                -- 低: 低价值客户群和 已流失
                WHEN rfm_segment IN ('潜力挽留客户', '新客培育', '低价值保持', '低价值挽留', '已流失', '无购买记录') THEN '低'
                ELSE '中'
            END
        """)
        p_updated = cursor.rowcount
        print(f"  ✅ 跟进优先级计算完成 ({p_updated} 条记录)")

    # 根据流失风险升级优先级
    print("  根据流失风险升级优先级...")
    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE target_buyers_precomputed
            SET follow_priority = '高'
            WHERE churn_risk = '高' AND follow_priority IN ('中', '低')
        """)
        upgraded = cursor.rowcount
        print(f"  ✅ 升级了 {upgraded} 条高流失风险客户")

    # 根据 VIP 等级升级优先级
    print("  根据 VIP 等级升级优先级...")
    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE target_buyers_precomputed
            SET follow_priority = '高'
            WHERE vip_level IN ('V3', 'V2') AND follow_priority = '中'
        """)
        v_upgraded = cursor.rowcount
        print(f"  ✅ 升级了 {v_upgraded} 条 VIP 客户")


def verify_migration(conn):
    """验证迁移结果"""
    print("\n" + "=" * 50)
    print("Phase 5: 验证迁移结果")
    print("-" * 50)

    # 检查是否有待分类客户
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM target_buyers_precomputed
            WHERE rfm_segment = '待分类'
        """)
        result = cursor.fetchone()
        unclassified_count = result['count'] if result else 0

        if unclassified_count > 0:
            print(f"  ⚠️ 发现 {unclassified_count} 条待分类客户！")
        else:
            print("  ✅ 无待分类客户，所有客户已正确分类")

    # RFM 分数分布
    print("\n📊 RFM 分数分布:")
    print("-" * 50)
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT rfm_recency_score, COUNT(*) as count
            FROM target_buyers_precomputed
            GROUP BY rfm_recency_score
            ORDER BY rfm_recency_score
        """)
        for row in cursor.fetchall():
            print(f"  R={row['rfm_recency_score']}: {row['count']} 条")

    # 客户分类分布
    print("\n📊 客户分类分布:")
    print("-" * 50)
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT rfm_segment, COUNT(*) as count,
                   ROUND(AVG(historical_net_sales), 2) as avg_netsales,
                   ROUND(AVG(total_orders), 2) as avg_orders
            FROM target_buyers_precomputed
            WHERE rfm_segment IS NOT NULL
            GROUP BY rfm_segment
            ORDER BY count DESC
        """)
        for row in cursor.fetchall():
            print(f"  {row['rfm_segment']}: {row['count']} 条 (平均消费: ¥{row['avg_netsales']}, 平均订单: {row['avg_orders']})")

    # 跟进优先级分布
    print("\n📊 跟进优先级分布:")
    print("-" * 50)
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT follow_priority, COUNT(*) as count
            FROM target_buyers_precomputed
            WHERE follow_priority IS NOT NULL
            GROUP BY follow_priority
            ORDER BY FIELD(follow_priority, '紧急', '高', '中', '低')
        """)
        for row in cursor.fetchall():
            print(f"  {row['follow_priority']}: {row['count']} 条")


def main():
    """主函数"""
    print("=" * 50)
    print("🚀 RFM 客户分类迁移脚本")
    print("=" * 50)

    # 加载数据库配置
    db_config = load_db_config()
    if not db_config:
        print("❌ 无法加载数据库配置文件 ~/database_config.json")
        sys.exit(1)

    # 获取数据库名称
    db_name = os.environ.get("DB_NAME_TO_USE", "aliyunDB")
    print(f"📦 使用数据库: {db_name}")

    # 获取连接
    conn = get_connection(db_config, db_name)

    try:
        # Phase 1: 迁移字段
        if not migrate_rfm_fields(conn):
            print("❌ 字段迁移失败")
            sys.exit(1)

        # Phase 2: 计算 RFM 分数
        calculate_rfm_scores(conn)

        # Phase 3: 确定 RFM 分类
        determine_rfm_segments(conn)

        # Phase 4: 计算跟进优先级
        calculate_follow_priority(conn)

        # Phase 5: 验证结果
        verify_migration(conn)

        print("\n" + "=" * 50)
        print("🎉 RFM 分类迁移完成!")
        print("=" * 50)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
