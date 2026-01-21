#!/usr/bin/env python3
"""
手动刷新目标买家预计算表
执行 CALL refresh_target_buyers_precomputed() 存储过程
"""
import sys
import os
import time
import io

# 设置标准输出编码为 UTF-8 (Windows兼容)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from backend.database import Database
from backend.config import settings

def refresh_target_buyers():
    """执行预计算表刷新"""
    print("🔄 开始刷新目标买家预计算表...")
    print("=" * 60)

    # 使用配置的数据库
    db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
    print(f"📊 使用数据库: {db_name}")

    db = Database(db_name=db_name)

    try:
        # 记录开始时间
        start_time = time.time()

        # 执行存储过程
        print("\n⚙️  执行存储过程: refresh_target_buyers_precomputed()")
        result = db.execute_query("CALL refresh_target_buyers_precomputed()")

        elapsed = time.time() - start_time
        print(f"\n✅ 刷新完成! 耗时: {elapsed:.2f}秒")

        # 验证结果
        print("\n" + "=" * 60)
        print("📊 验证刷新结果:")
        print("=" * 60)

        # 总买家数
        total = db.execute_query("SELECT COUNT(*) as count FROM target_buyers_precomputed")
        print(f"👥 目标买家总数: {total[0]['count']:,}")

        # 按类型统计
        print("\n📈 按类型分布:")
        type_stats = db.execute_query(
            "SELECT buyer_type, COUNT(*) as count FROM target_buyers_precomputed GROUP BY buyer_type"
        )
        for row in type_stats:
            print(f"   {row['buyer_type']}: {row['count']:,}")

        # VIP等级分布
        print("\n⭐ VIP等级分布:")
        vip_stats = db.execute_query(
            """SELECT vip_level, COUNT(*) as count, AVG(rolling_24m_netsales) as avg_netsales
            FROM target_buyers_precomputed
            GROUP BY vip_level
            ORDER BY
                CASE vip_level
                    WHEN 'V3' THEN 1
                    WHEN 'V2' THEN 2
                    WHEN 'V1' THEN 3
                    WHEN 'V0' THEN 4
                    ELSE 5
                END"""
        )
        for row in vip_stats:
            avg_sales = row['avg_netsales'] or 0
            print(f"   {row['vip_level']}: {row['count']:,} (平均销售: ¥{avg_sales:,.0f})")

        # 最后更新时间
        last_update = db.execute_query("SELECT MAX(updated_at) as last_update FROM target_buyers_precomputed")
        print(f"\n🕐 最后更新时间: {last_update[0]['last_update']}")

        print("\n" + "=" * 60)
        print("✅ 刷新成功完成!")

    except Exception as e:
        print(f"\n❌ 刷新失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        db.close()

if __name__ == "__main__":
    refresh_target_buyers()
