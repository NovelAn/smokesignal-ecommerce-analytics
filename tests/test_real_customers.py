"""
测试真实客户数据的AI分析
"""
import sys
import os
import io
import json
import time

# 设置UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.ai.analyzer_orchestrator import AnalyzerOrchestrator
from backend.database import Database
from backend.config import settings


def print_section(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def get_real_buyers_with_chats(limit=10):
    """获取有聊天记录的真实客户"""
    db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
    db = Database(db_name=db_name)

    query = """
        SELECT buyer_nick, vip_level, city, l6m_netsales, total_orders,
               last_chat_date, top_category
        FROM target_buyers_precomputed
        WHERE last_chat_date IS NOT NULL
        ORDER BY last_chat_date DESC
        LIMIT %s
    """

    buyers = db.execute_query(query, [limit])
    return buyers


def get_real_buyers_without_chats(limit=10):
    """获取没有聊天记录的真实客户"""
    db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
    db = Database(db_name=db_name)

    query = """
        SELECT buyer_nick, vip_level, city, l6m_netsales, total_orders,
               top_category, discount_ratio
        FROM target_buyers_precomputed
        WHERE last_chat_date IS NULL
        ORDER BY l6m_netsales DESC
        LIMIT %s
    """

    buyers = db.execute_query(query, [limit])
    return buyers


def get_buyer_full_profile(buyer_nick):
    """获取客户完整profile"""
    from backend.analytics.target_buyer_analyzer import TargetBuyerAnalyzer

    analyzer = TargetBuyerAnalyzer()
    profile = analyzer.get_buyer_profile(buyer_nick)
    return profile


def get_buyer_chats(buyer_nick, limit=30):
    """获取客户聊天记录"""
    from backend.database import BuyerQueries

    db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
    db = Database(db_name=db_name)

    query, params = BuyerQueries.get_chat_messages(buyer_nick, limit)
    chats = db.execute_query(query, params)
    return chats


def get_buyer_orders(buyer_nick, limit=50):
    """获取客户订单"""
    db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
    db = Database(db_name=db_name)

    query = """
        SELECT 订单号, 商品名称 as commodity_name, category,
               成交总金额 as payment, 退款金额, 退款类型 as refund_status,
               最后付款时间 as pay_time
        FROM target_buyer_orders
        WHERE 买家昵称 = %s
        ORDER BY 最后付款时间 DESC
        LIMIT %s
    """

    orders = db.execute_query(query, [buyer_nick, limit])
    return orders


def test_real_customer_with_chats():
    """测试有聊天记录的真实客户"""
    print_section("测试1: 有聊天记录的真实客户")

    # 获取有聊天记录的客户
    buyers = get_real_buyers_with_chats(limit=5)

    if not buyers:
        print("⚠️  未找到有聊天记录的客户")
        return None

    # 选择第一个客户进行测试
    buyer = buyers[0]
    buyer_nick = buyer['buyer_nick']  # 买家昵称

    print(f"\n测试客户: {buyer_nick}")
    print(f"VIP等级: {buyer['vip_level']}")
    print(f"城市: {buyer['city']}")
    print(f"L6M消费: ¥{float(buy['l6m_netsales']):,.0f}")
    print(f"订单数: {buyer['total_orders']}")
    print(f"品类: {buyer['top_category']}")
    print(f"最后聊天: {buyer['last_chat_date']}")

    # 获取完整数据
    profile = get_buyer_full_profile(buyer_nick)
    chats = get_buyer_chats(buyer_nick, limit=30)
    orders = get_buyer_orders(buy_nick, limit=50)

    print(f"\n数据获取:")
    print(f"  - Profile字段数: {len(profile) if profile else 0}")
    print(f"  - 聊天记录数: {len(chats)}")
    print(f"  - 订单记录数: {len(orders)}")

    # AI分析
    orchestrator = AnalyzerOrchestrator()

    print(f"\n开始AI分析...")
    start_time = time.time()

    result = orchestrator.analyze_buyer_persona(
        buyer_nick=buyer_nick,
        profile=profile,
        chats=chats,
        orders=orders
    )

    elapsed_time = time.time() - start_time

    print(f"\n【AI分析结果】")
    print(f"分析方法: {result.get('analysis_method', 'Unknown')}")
    print(f"数据来源: {result.get('data_source', 'Unknown')}")
    print(f"置信度: {result.get('confidence_level', 'Unknown')}")
    print(f"耗时: {elapsed_time:.1f}秒")

    print(f"\n总结:")
    print(f"  {result.get('summary', '')}")

    print(f"\n兴趣点:")
    for interest in result.get('key_interests', [])[:3]:
        print(f"  • {interest}")

    print(f"\n痛点:")
    for pain_point in result.get('pain_points', [])[:2]:
        print(f"  • {pain_point}")

    print(f"\n建议:")
    print(f"  {result.get('recommended_action', '')}")

    # 验证质量
    summary = result.get('summary', '')

    print(f"\n【质量检查】")
    if "客户是一个" in summary or "客单价¥" in summary or "退款率" in summary:
        print("✅ 使用了正确的总结格式")
    else:
        print("⚠️  总结格式可能不符合要求")

    if "追求品质" in summary or "注重性价比" in summary or "向往" in summary:
        print("❌ 包含废话词汇")
    else:
        print("✅ 没有废话词汇")

    return result


def test_real_customer_without_chats():
    """测试没有聊天记录的真实客户"""
    print_section("测试2: 无聊天记录的真实客户")

    # 获取无聊天记录的客户
    buyers = get_real_buyers_without_chats(limit=5)

    if not buyers:
        print("⚠️  未找到无聊天记录的客户")
        return None

    # 选择第一个客户进行测试
    buyer = buyers[0]
    buyer_nick = buyer['buyer_nick']  # 买家昵称

    print(f"\n测试客户: {buyer_nick}")
    print(f"VIP等级: {buyer['vip_level']}")
    print(f"城市: {buyer['city']}")
    print(f"L6M消费: ¥{float(buyer['l6m_netsales']):,.0f}")
    print(f"订单数: {buyer['total_orders']}")
    print(f"品类: {buyer['top_category']}")
    print(f"折扣率: {float(buy['discount_ratio']):.1%}" if buyer.get('discount_ratio') else "N/A")

    # 获取完整数据
    profile = get_buyer_full_profile(buy_nick)
    chats = []  # 没有聊天记录
    orders = get_buyer_orders(buy_nick, limit=50)

    print(f"\n数据获取:")
    print(f"  - Profile字段数: {len(profile) if profile else 0}")
    print(f"  - 聊天记录数: 0 (无)")
    print(f"  - 订单记录数: {len(orders)}")

    # AI分析
    orchestrator = AnalyzerOrchestrator()

    print(f"\n开始AI分析...")
    start_time = time.time()

    result = orchestrator.analyze_buyer_persona(
        buyer_nick=buyer_nick,
        profile=profile,
        chats=chats,
        orders=orders
    )

    elapsed_time = time.time() - start_time

    print(f"\n【AI分析结果】")
    print(f"分析方法: {result.get('analysis_method', 'Unknown')}")
    print(f"数据来源: {result.get('data_source', 'Unknown')}")
    print(f"置信度: {result.get('confidence_level', 'Unknown')}")
    print(f"耗时: {elapsed_time:.1f}秒")

    print(f"\n总结:")
    print(f"  {result.get('summary', '')}")

    print(f"\n兴趣点:")
    for interest in result.get('key_interests', [])[:3]:
        print(f"  • {interest}")

    print(f"\n痛点:")
    for pain_point in result.get('pain_points', [])[:2]:
        print(f"  • {pain_point}")

    print(f"\n建议:")
    print(f"  {result.get('recommended_action', '')}")

    # 验证质量
    summary = result.get('summary', '')

    print(f"\n【质量检查】")
    if any(word in summary for word in ["客单价¥", "退款率", "占比", "折扣率"]):
        print("✅ 使用了具体数字")
    else:
        print("⚠️  可能缺少具体数字")

    if "追求品质" in summary or "注重性价比" in summary or "向往" in summary:
        print("❌ 包含废话词汇")
    else:
        print("✅ 没有废话词汇")

    return result


def main():
    """运行所有真实客户测试"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*15 + "AI分析真实客户数据测试" + " "*29 + "║")
    print("╚" + "="*78 + "╝")

    try:
        # 测试1: 有聊天记录的客户
        result1 = test_real_customer_with_chats()

        # 等待一下
        print("\n按Enter继续测试无聊天记录客户...")
        # input()

        # 测试2: 无聊天记录的客户
        result2 = test_real_customer_without_chats()

        print_section("测试完成")

        print("\n✅ 真实客户数据测试完成！")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
