"""
清除所有客户的 Sentiment/Intent 分析缓存
用于在更新分析逻辑后重新运行批量分析

执行方式: python scripts/clear_sentiment_cache.py
"""
import sys
import os
import io

# 设置UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import Database
from backend.config import settings


def clear_sentiment_cache():
    """清除所有 sentiment 缓存"""

    db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
    db = Database(db_name=db_name)

    print("=" * 60)
    print("清除 Sentiment/Intent 分析缓存")
    print("=" * 60)

    # 1. 清除缓存表中的 sentiment 相关字段
    print("\n[1] 清除 buyer_ai_analysis_cache 表中的 sentiment 数据...")

    clear_cache_query = """
        UPDATE buyer_ai_analysis_cache
        SET
            sentiment_score = NULL,
            sentiment_label = NULL,
            intent_distribution = NULL,
            dominant_intent = NULL,
            pre_sale_keywords = NULL,
            post_sale_keywords = NULL,
            complaint_count = 0,
            sentiment_method = NULL,
            sentiment_analyzed_at = NULL,
            sentiment_analyzed_last_chat_date = NULL
    """

    cache_result = db.execute_update(clear_cache_query)
    print(f"  清除了 {cache_result} 条缓存记录的 sentiment 数据")

    # 2. 清除预计算表中的 sentiment/intent 字段
    print("\n[2] 清除 target_buyers_precomputed 表中的 sentiment/intent 数据...")

    clear_precomputed_query = """
        UPDATE target_buyers_precomputed
        SET
            sentiment_label = NULL,
            sentiment_score = NULL,
            dominant_intent = NULL,
            pre_sale_score = 0,
            post_sale_score = 0
        WHERE sentiment_score IS NOT NULL
           OR pre_sale_score > 0
           OR post_sale_score > 0
    """

    precomputed_result = db.execute_update(clear_precomputed_query)
    print(f"  清除了 {precomputed_result} 条预计算记录的 sentiment/intent 数据")

    # 3. 验证清除结果
    print("\n[3] 验证清除结果...")

    verify_query = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN sentiment_score IS NOT NULL THEN 1 ELSE 0 END) as has_sentiment,
            SUM(CASE WHEN pre_sale_score > 0 OR post_sale_score > 0 THEN 1 ELSE 0 END) as has_intent
        FROM target_buyers_precomputed
    """
    result = db.execute_query(verify_query)
    if result:
        print(f"  总客户数: {result[0].get('total')}")
        print(f"  有 sentiment 数据: {result[0].get('has_sentiment')}")
        print(f"  有 intent scores: {result[0].get('has_intent')}")

    print("\n" + "=" * 60)
    print("缓存清除完成!")
    print("=" * 60)
    print("\n下一步操作:")
    print("1. 在前端点击「批量情感分析」按钮")
    print("2. 或者调用 API: POST /api/v2/ai/batch-analyze")


if __name__ == "__main__":
    clear_sentiment_cache()
