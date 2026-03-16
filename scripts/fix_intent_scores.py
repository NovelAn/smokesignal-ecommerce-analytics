"""
修复 intent scores - 从现有的 intent_distribution 数据计算并更新
用于修复 pre_sale_score 和 post_sale_score 为 0 的问题

执行方式: python scripts/fix_intent_scores.py
"""
import sys
import os
import io
import json

# 设置UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import Database
from backend.config import settings
from backend.analytics.tag_calculator import TagCalculator


def fix_intent_scores():
    """修复 intent scores - 从缓存表的 intent_distribution 计算"""

    db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
    db = Database(db_name=db_name)

    print("=" * 60)
    print("修复 Intent Scores (从 intent_distribution 计算)")
    print("=" * 60)

    # 1. 查找所有有 intent_distribution 但 pre_sale_score=0 的客户
    print("\n[1] 查找需要修复的客户...")

    query = """
        SELECT
            cache.buyer_nick,
            cache.intent_distribution,
            tb.pre_sale_score,
            tb.post_sale_score
        FROM buyer_ai_analysis_cache cache
        JOIN target_buyers_precomputed tb
            ON cache.buyer_nick = tb.buyer_nick
        WHERE cache.intent_distribution IS NOT NULL
          AND tb.pre_sale_score = 0
          AND tb.post_sale_score = 0
    """

    buyers = db.execute_query(query)

    if not buyers:
        print("  [OK] 所有客户的 intent scores 都是完整的!")
        return

    print(f"  发现 {len(buyers)} 个客户需要修复 intent scores")

    # 2. 逐个计算并更新
    print("\n[2] 开始修复...")

    fixed_count = 0
    error_count = 0

    for buyer in buyers:
        buyer_nick = buyer.get('buyer_nick')
        intent_dist_str = buyer.get('intent_distribution')

        try:
            # 解析 intent_distribution
            if isinstance(intent_dist_str, str):
                intent_dist = json.loads(intent_dist_str)
            else:
                intent_dist = intent_dist_str

            if not intent_dist:
                continue

            # 使用 TagCalculator 计算 scores
            scores = TagCalculator.calculate_intent_scores(intent_dist)
            pre_sale_score = scores['pre_sale_score']
            post_sale_score = scores['post_sale_score']
            dominant_intent = scores['dominant_intent']

            # 更新数据库
            update_query = """
                UPDATE target_buyers_precomputed
                SET
                    pre_sale_score = %s,
                    post_sale_score = %s,
                    dominant_intent = %s
                WHERE buyer_nick = %s
            """

            db.execute_update(update_query, [
                pre_sale_score,
                post_sale_score,
                dominant_intent,
                buyer_nick
            ])

            fixed_count += 1
            print(f"  [OK] {buyer_nick}: pre_sale={pre_sale_score}, post_sale={post_sale_score}, intent={dominant_intent}")

        except Exception as e:
            error_count += 1
            print(f"  [FAIL] {buyer_nick}: {str(e)[:50]}")

    # 3. 输出统计
    print("\n" + "=" * 60)
    print("修复完成!")
    print("=" * 60)
    print(f"  处理客户数: {len(buyers)}")
    print(f"  成功修复: {fixed_count}")
    print(f"  失败数: {error_count}")

    # 4. 验证结果
    print("\n[验证] 检查修复后的数据...")
    verify_query = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN pre_sale_score > 0 OR post_sale_score > 0 THEN 1 ELSE 0 END) as has_scores
        FROM target_buyers_precomputed
    """
    result = db.execute_query(verify_query)
    if result:
        print(f"  总客户数: {result[0].get('total')}")
        print(f"  有 intent scores 的客户数: {result[0].get('has_scores')}")


if __name__ == "__main__":
    fix_intent_scores()
