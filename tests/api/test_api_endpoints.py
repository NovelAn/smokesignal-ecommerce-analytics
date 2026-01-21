"""
测试后端 API 端点
"""
import requests
import json
import sys
import io
from typing import Dict, Any

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_BASE_URL = "http://localhost:8000/api"

def test_api(name: str, url: str) -> bool:
    """测试一个 API 端点"""
    try:
        print(f"\n{name}:")
        print(f"  GET {url}")
        response = requests.get(f"{API_BASE_URL}{url}", timeout=10)

        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ 成功 (200)")

            # 显示部分数据
            if isinstance(data, list):
                print(f"  返回: {len(data)} 条记录")
                if data:
                    print(f"  样本: {json.dumps(data[0], ensure_ascii=False)[:100]}")
            elif isinstance(data, dict):
                print(f"  返回: {list(data.keys())}")
                if 'buyers' in data:
                    print(f"  买家数: {data.get('total', 'N/A')}")
            return True
        else:
            print(f"  ❌ 失败 ({response.status_code}): {response.text[:100]}")
            return False
    except Exception as e:
        print(f"  ❌ 错误: {str(e)[:100]}")
        return False

print("=" * 60)
print("测试后端 API 端点")
print("=" * 60)

results = []

# 测试各个端点
results.append(test_api("1. 获取买家列表", "/buyers?limit=5"))
results.append(test_api("2. Dashboard 指标", "/dashboard/metrics"))
results.append(test_api("3. 每日统计", "/dashboard/daily-stats?days=7"))
results.append(test_api("4. 需关注客户", "/dashboard/actionable-customers"))

# 测试单个买家数据
print("\n" + "=" * 60)
print("测试单个买家数据端点")
print("=" * 60)

# 获取一个买家昵称
try:
    buyers_response = requests.get(f"{API_BASE_URL}/buyers?limit=1", timeout=10)
    if buyers_response.status_code == 200:
        buyers_data = buyers_response.json()
        if buyers_data.get('buyers'):
            first_buyer = buyers_data['buyers'][0]
            print(f"\n使用买家: {first_buyer}")

            results.append(test_api("5. 买家画像", f"/buyers/{first_buyer}"))
            results.append(test_api("6. 买家订单", f"/buyers/{first_buyer}/orders?limit=3"))
            results.append(test_api("7. 买家聊天", f"/buyers/{first_buyer}/chats?limit=3"))
        else:
            print("  ⚠️  没有找到买家数据")
    else:
        print("  ⚠️  无法获取买家列表")
except Exception as e:
    print(f"  ⚠️  错误: {e}")

# 总结
print("\n" + "=" * 60)
print(f"测试完成: {sum(results)}/{len(results)} 个端点正常")
print("=" * 60)
