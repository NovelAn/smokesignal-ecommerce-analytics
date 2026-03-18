"""
AI分析测试脚本 - 快速验证新系统
"""
import sys
import os
import io

# 设置UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.ai.analyzer_orchestrator import AnalyzerOrchestrator


def test_new_user_analysis():
    """测试新手客户分析"""
    print("\n" + "="*80)
    print("测试用例 1: 新手客户（贺子洋715）")
    print("="*80)

    orchestrator = AnalyzerOrchestrator()

    result = orchestrator.analyze_buyer_persona(
        buyer_nick="贺子洋715",
        profile={
            "vip_level": "V1",
            "city": "北京",
            "l6m_netsales": 5000,
            "l1y_netsales": 8000,
            "buyer_type": "New",
            "first_purchase_date": "2026-01-15",
            "last_purchase_date": "2026-01-20",
            "top_category": "PIPES",
            "total_orders": 2
        },
        chats=[
            {"content": "我是新手，不知道怎么选pipe", "sender": "贺子洋715", "msg_time": "2026-01-28 10:00:00"},
            {"content": "有什么适合入门的吗", "sender": "贺子洋715", "msg_time": "2026-01-28 10:05:00"},
            {"content": "这个怎么用啊", "sender": "贺子洋715", "msg_time": "2026-01-28 10:10:00"}
        ],
        orders=[]
    )

    print("\n【分析结果】")
    print(f"分析方法: {result.get('analysis_method', 'Unknown')}")
    print(f"总结: {result.get('summary', '')}")
    print(f"兴趣点: {result.get('key_interests', [])}")
    print(f"痛点: {result.get('pain_points', [])}")
    print(f"建议: {result.get('recommended_action', '')}")
    print(f"置信度: {result.get('confidence_level', '')}")

    # 验证新手识别
    summary = result.get('summary', '')
    if "新手" in summary or "入门" in summary:
        print("\n✅ 测试通过：正确识别为新手客户")
    else:
        print("\n❌ 测试失败：未能识别为新手客户")

    return result


def test_expert_user_analysis():
    """测试专家客户分析"""
    print("\n" + "="*80)
    print("测试用例 2: 专家客户（pipe_expert）")
    print("="*80)

    orchestrator = AnalyzerOrchestrator()

    result = orchestrator.analyze_buyer_persona(
        buyer_nick="pipe_expert",
        profile={
            "vip_level": "V3",
            "city": "上海",
            "l6m_netsales": 50000,
            "l1y_netsales": 80000,
            "buyer_type": "Old",
            "first_purchase_date": "2024-01-01",
            "last_purchase_date": "2026-01-25",
            "top_category": "PIPES",
            "total_orders": 20
        },
        chats=[
            {"content": "这款的产地是哪里？", "sender": "pipe_expert", "msg_time": "2026-01-28 10:00:00"},
            {"content": "briar的grain怎么样", "sender": "pipe_expert", "msg_time": "2026-01-28 10:05:00"},
            {"content": "和XX品牌的finish有什么区别", "sender": "pipe_expert", "msg_time": "2026-01-28 10:10:00"}
        ],
        orders=[]
    )

    print("\n【分析结果】")
    print(f"分析方法: {result.get('analysis_method', 'Unknown')}")
    print(f"总结: {result.get('summary', '')}")
    print(f"兴趣点: {result.get('key_interests', [])}")
    print(f"痛点: {result.get('pain_points', [])}")
    print(f"建议: {result.get('recommended_action', '')}")
    print(f"置信度: {result.get('confidence_level', '')}")

    # 验证专家识别
    summary = result.get('summary', '')
    if "专业" in summary or "资深" in summary or "专家" in summary:
        print("\n✅ 测试通过：正确识别为专家客户")
    else:
        print("\n❌ 测试失败：未能识别为专家客户")

    return result


def main():
    """运行所有测试"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "AI增强分析系统 - 功能测试" + " "*20 + "║")
    print("╚" + "="*78 + "╝")

    try:
        # 测试新手客户
        test_new_user_analysis()

        # 测试专家客户
        test_expert_user_analysis()

        print("\n" + "="*80)
        print("✅ 所有测试完成")
        print("="*80)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
