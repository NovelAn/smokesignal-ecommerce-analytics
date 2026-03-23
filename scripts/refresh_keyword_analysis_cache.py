"""
关键词分析预计算脚本
从聊天记录中提取关键词，按客户类型和分类聚合，存入缓存表

运行方式:
    PYTHONPATH=. python scripts/refresh_keyword_analysis_cache.py
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from collections import Counter
from backend.database.connection import Database
from backend.analytics.keyword_categories import KEYWORD_CATEGORIES, KEYWORD_TO_CATEGORY, CATEGORY_LIST


def get_buyer_types_map(db: Database) -> dict:
    """
    获取客户类型映射: buyer_nick -> buyer_type
    从 target_buyers_precomputed 表获取
    """
    query = """
        SELECT buyer_nick, buyer_type
        FROM target_buyers_precomputed
        WHERE buyer_type IS NOT NULL
    """
    results = db.execute_query(query)
    return {row['buyer_nick']: row['buyer_type'] for row in results}


def get_customer_messages(db: Database) -> list:
    """
    获取所有客户消息（sender_nick = user_nick）
    过滤掉纯链接、纯数字等无意义消息
    """
    query = """
        SELECT user_nick, content
        FROM chat_history
        WHERE sender_nick = user_nick
          AND content IS NOT NULL
          AND content != ''
          AND LENGTH(content) > 2
    """
    results = db.execute_query(query)

    # 过滤无意义消息
    meaningful = []
    for row in results:
        content = row['content'].strip()
        # 过滤纯链接
        if content.startswith('http'):
            continue
        # 过滤纯数字
        if content.isdigit():
            continue
        # 过滤太短的消息
        if len(content) < 3:
            continue
        meaningful.append({
            'user_nick': row['user_nick'],
            'content': content
        })

    return meaningful


def extract_keywords_from_text(content: str) -> list:
    """
    从文本中提取关键词
    返回: [(category, keyword), ...]
    """
    keywords = []
    for keyword, category in KEYWORD_TO_CATEGORY.items():
        if keyword in content:
            keywords.append((category, keyword))
    return keywords


def analyze_messages(messages: list, buyer_types_map: dict) -> dict:
    """
    分析消息，按客户类型聚合关键词

    Args:
        messages: 消息列表，每条消息包含 user_nick 和 content
        buyer_types_map: 客户类型映射，key 是 buyer_nick（需要与 user_nick 匹配）

    Returns:
        {
            'ALL': {
                'keywords': Counter({('赠品', '赠品'): 45, ...}),
                'categories': Counter({'赠品': 112, ...}),
                'total': 1000
            },
            'SMOKER': { ... },
            ...
        }
    """
    # 初始化各客户类型的数据结构（只保留有效的客户类型）
    analysis = {}
    buyer_types = ['ALL', 'SMOKER', 'BOTH', 'VIC']

    for bt in buyer_types:
        analysis[bt] = {
            'keywords': Counter(),
            'categories': Counter(),
            'total': 0
        }

    for msg in messages:
        user_nick = msg['user_nick']
        content = msg['content']
        # buyer_types_map 的 key 是 buyer_nick，需要与 user_nick 匹配
        buyer_type = buyer_types_map.get(user_nick)

        # 提取关键词
        keywords = extract_keywords_from_text(content)

        if not keywords:
            continue

        # 更新 ALL 统计
        analysis['ALL']['total'] += 1
        for category, keyword in keywords:
            analysis['ALL']['keywords'][(category, keyword)] += 1
            analysis['ALL']['categories'][category] += 1

        # 更新具体客户类型统计（只统计已分类的客户）
        if buyer_type and buyer_type in analysis:
            analysis[buyer_type]['total'] += 1
            for category, keyword in keywords:
                analysis[buyer_type]['keywords'][(category, keyword)] += 1
                analysis[buyer_type]['categories'][category] += 1

    return analysis


def refresh_cache_tables(db: Database, analysis: dict):
    """
    刷新缓存表
    """
    # 清空现有数据
    db.execute_update("TRUNCATE TABLE keyword_analysis_cache")
    db.execute_update("TRUNCATE TABLE category_distribution_cache")
    db.execute_update("TRUNCATE TABLE keyword_analysis_meta")

    for buyer_type, data in analysis.items():
        total = data['total']
        keywords = data['keywords']
        categories = data['categories']

        # 计算总关键词数（用于计算占比）
        total_keyword_count = sum(keywords.values())
        total_category_count = sum(categories.values())

        # 插入关键词数据
        for (category, keyword), count in keywords.most_common(500):  # 限制TOP 500
            percentage = round(count / total_keyword_count * 100, 2) if total_keyword_count > 0 else 0
            db.execute_update(
                """
                INSERT INTO keyword_analysis_cache (buyer_type, category, keyword, count, percentage)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (buyer_type, category, keyword, count, percentage)
            )

        # 插入分类分布数据
        for category, count in categories.items():
            percentage = round(count / total_category_count * 100, 2) if total_category_count > 0 else 0
            db.execute_update(
                """
                INSERT INTO category_distribution_cache (buyer_type, category, count, percentage)
                VALUES (%s, %s, %s, %s)
                """,
                (buyer_type, category, count, percentage)
            )

        # 插入元数据
        db.execute_update(
            """
            INSERT INTO keyword_analysis_meta (buyer_type, total_messages, analyzed_messages)
            VALUES (%s, %s, %s)
            """,
            (buyer_type, total, total)
        )

        print(f"  {buyer_type}: {total} messages, {len(keywords)} unique keywords")


def main():
    print("=" * 60)
    print("关键词分析预计算脚本")
    print("=" * 60)

    # 连接数据库
    print("\n1. 连接数据库...")
    db = Database('aliyunDB')

    # 获取客户类型映射
    print("\n2. 获取客户类型映射...")
    buyer_types_map = get_buyer_types_map(db)
    print(f"   找到 {len(buyer_types_map)} 个已分类客户")

    # 获取客户消息
    print("\n3. 获取客户消息...")
    messages = get_customer_messages(db)
    print(f"   找到 {len(messages)} 条有效消息")

    # 分析消息
    print("\n4. 分析关键词...")
    analysis = analyze_messages(messages, buyer_types_map)

    # 刷新缓存表
    print("\n5. 刷新缓存表...")
    refresh_cache_tables(db, analysis)

    print("\n" + "=" * 60)
    print("预计算完成!")
    print("=" * 60)

    # 打印摘要
    print("\n摘要:")
    for buyer_type, data in analysis.items():
        if data['total'] > 0:
            top_keywords = data['keywords'].most_common(5)
            print(f"\n  {buyer_type} ({data['total']} 条消息):")
            for (cat, kw), count in top_keywords:
                print(f"    - {kw} ({cat}): {count}")


if __name__ == '__main__':
    main()
