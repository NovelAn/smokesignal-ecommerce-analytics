"""
测试真实客户AI分析 - 简化版本
通过API直接测试
"""
import sys
import os
import io
import json
import time

# 设置UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests

BASE_URL = "http://localhost:8002/api/v2"


def test_with_chats_customer():
    """测试有聊天记录的客户"""
    print("\n" + "="*80)
    print("测试1: 有聊天记录的客户 → 应该用DeepSeek-R1")
    print("="*80)

    # 获取有聊天记录的客户列表（需要更多数据才能找到有聊天记录的客户）
    response = requests.get(f"{BASE_URL}/buyers?limit=200")
    data = response.json()
    buyers = data.get('buyers', [])

    # 筛选有聊天记录的客户（使用l3m_chat_frequency_days判断）
    buyers_with_chats = [b for b in buyers if b.get('l3m_chat_frequency_days', 0) > 0]

    if not buyers_with_chats:
        print("⚠️  未找到有聊天记录的客户")
        return

    # 选择前3个客户测试
    for i, buyer in enumerate(buyers_with_chats[:3]):
        buyer_nick = buyer['buyer_nick']

        print(f"\n{'='*60}")
        print(f"客户 {i+1}: {buyer_nick}")
        print(f"VIP: {buyer['vip_level']}")
        print(f"品类: {buyer['top_category']}")
        print(f"L6M: ¥{buyer['l6m_netsales']}")
        print(f"聊天活跃度: {buyer['l3m_chat_frequency_days']}天/3月")

        # 调用AI分析
        print(f"\n正在AI分析...")
        start = time.time()

        try:
            api_response = requests.get(
                f"{BASE_URL}/buyers/{buyer_nick}?include_ai=true",
                timeout=60
            )
            elapsed = time.time() - start

            if api_response.status_code == 200:
                result = api_response.json()
                ai = result.get('ai_analysis', {})

                print(f"✅ 分析完成 (耗时: {elapsed:.1f}秒)")
                print(f"方法: {ai.get('analysis_method', 'Unknown')}")
                print(f"数据来源: {ai.get('data_source', 'Unknown')}")
                print(f"\n总结:")
                print(f"  {ai.get('summary', '无')[:300]}...")

                # 质量检查
                summary = ai.get('summary', '')
                print(f"\n质量检查:")

                if any(word in summary for word in ["客户是一个", "客单价¥", "退款率", "占比"]):
                    print("  ✅ 使用正确格式")
                else:
                    print("  ⚠️  格式可能需要优化")

                if "追求品质" in summary or "注重性价比" in summary or "向往" in summary:
                    print("  ❌ 包含废话词汇")
                else:
                    print("  ✅ 没有废话词汇")

            else:
                print(f"❌ API错误: {api_response.status_code}")

        except Exception as e:
            print(f"❌ 分析失败: {e}")


def test_without_chats_customer():
    """测试没有聊天记录的客户"""
    print("\n" + "="*80)
    print("测试2: 无聊天记录的客户 → 应该用Zhipu")
    print("="*80)

    # 获取无聊天记录的客户列表
    response = requests.get(f"{BASE_URL}/buyers?limit=200")
    data = response.json()
    buyers = data.get('buyers', [])

    # 筛选没有聊天记录的客户（l3m_chat_frequency_days为0或NULL）
    buyers_without_chats = [b for b in buyers if b.get('l3m_chat_frequency_days', 0) == 0]

    if not buyers_without_chats:
        print("⚠️  未找到无聊天记录的客户")
        return

    # 选择前3个客户测试
    for i, buyer in enumerate(buyers_without_chats[:3]):
        buyer_nick = buyer['buyer_nick']

        print(f"\n{'='*60}")
        print(f"客户 {i+1}: {buyer_nick}")
        print(f"VIP: {buyer['vip_level']}")
        print(f"品类: {buyer['top_category']}")
        print(f"L6M: ¥{buyer['l6m_netsales']}")
        print(f"聊天活跃度: 无聊天记录 (0天)")

        # 调用AI分析
        print(f"\n正在AI分析...")
        start = time.time()

        try:
            api_response = requests.get(
                f"{BASE_URL}/buyers/{buyer_nick}?include_ai=true",
                timeout=60
            )
            elapsed = time.time() - start

            if api_response.status_code == 200:
                result = api_response.json()
                ai = result.get('ai_analysis', {})

                print(f"✅ 分析完成 (耗时: {elapsed:.1f}秒)")
                print(f"方法: {ai.get('analysis_method', 'Unknown')}")
                print(f"数据来源: {ai.get('data_source', 'Unknown')}")
                print(f"\n总结:")
                print(f"  {ai.get('summary', '无')[:300]}...")

                # 质量检查
                summary = ai.get('summary', '')
                print(f"\n质量检查:")

                if any(word in summary for word in ["客单价¥", "退款率", "占比", "折扣率"]):
                    print("  ✅ 使用具体数字")
                else:
                    print("  ⚠️  可能缺少具体数字")

                if "追求品质" in summary or "注重性价比" in summary or "向往" in summary:
                    print("  ❌ 包含废话词汇")
                else:
                    print("  ✅ 没有废话词汇")

            else:
                print(f"❌ API错误: {api_response.status_code}")

        except Exception as e:
            print(f"❌ 分析失败: {e}")


def main():
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*15 + "AI分析真实客户数据测试" + " "*29 + "║")
    print("╚" + "="*78 + "╝")

    try:
        # 测试有聊天记录的客户
        test_with_chats_customer()

        # 测试无聊天记录的客户
        test_without_chats_customer()

        print("\n" + "="*80)
        print("✅ 真实客户数据测试完成！")
        print("="*80)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
