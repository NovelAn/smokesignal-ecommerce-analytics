"""
测试前后端 API 集成
"""
import requests
import sys
import io
from typing import Dict, Any

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_BASE_URL = "http://localhost:8000/api"

print("=" * 60)
print("测试后端 API - 用于前端集成")
print("=" * 60)

# 测试 Dashboard Metrics
print("\n1. Dashboard 指标:")
try:
    response = requests.get(f"{API_BASE_URL}/dashboard/metrics", timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f"  ✅ 成功")
        print(f"  - 总买家数: {data['total_buyers']:,}")
        print(f"  - 总订单数: {data['total_orders']:,}")
        print(f"  - 聊天消息总数: {data['total_chats']:,}")
        print(f"  - 平均客户价值: ¥{data['avg_ltv']:.2f}")
        print(f"  - VIP 分布: {data['vip_distribution']}")
    else:
        print(f"  ❌ 失败: {response.status_code}")
except Exception as e:
    print(f"  ❌ 错误: {e}")

# 测试 Actionable Customers
print("\n2. 需关注客户:")
try:
    response = requests.get(f"{API_BASE_URL}/dashboard/actionable-customers", timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f"  ✅ 成功 - {len(data)} 位客户需要关注")
        if data:
            print(f"  样本: {data[0]['user_nick']} - {data[0]['issue_type']} ({data[0]['priority']})")
    else:
        print(f"  ❌ 失败: {response.status_code}")
except Exception as e:
    print(f"  ❌ 错误: {e}")

# 测试 Buyers List
print("\n3. 买家列表:")
try:
    response = requests.get(f"{API_BASE_URL}/buyers?limit=10", timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f"  ✅ 成功 - 共 {data['total']} 位买家")
        print(f"  前10位: {', '.join(data['buyers'][:5])}...")
    else:
        print(f"  ❌ 失败: {response.status_code}")
except Exception as e:
    print(f"  ❌ 错误: {e}")

print("\n" + "=" * 60)
print("前端应用地址: http://localhost:3000")
print("后端 API 地址: http://localhost:8000/api")
print("=" * 60)
