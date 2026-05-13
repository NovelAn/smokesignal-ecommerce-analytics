"""
分析客户聊天记录中的关键词
用于设计 SMOKER 客户词云分析的分类体系
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from backend.database.connection import Database
from collections import Counter
import re

# 连接数据库
db = Database('aliyunDB')

# 查询客户发送的消息总数
result = db.execute_query('''
    SELECT COUNT(*) as total
    FROM chat_history
    WHERE sender_nick = user_nick
''')
print(f'客户消息总数: {result[0]["total"]}')

# 查询有消息的唯一客户数
result = db.execute_query('''
    SELECT COUNT(DISTINCT user_nick) as cnt
    FROM chat_history
    WHERE sender_nick = user_nick
''')
print(f'有消息的客户数: {result[0]["cnt"]}')

# 获取所有客户消息内容
print("\n正在提取所有客户消息...")
all_messages = db.execute_query('''
    SELECT content
    FROM chat_history
    WHERE sender_nick = user_nick
      AND content IS NOT NULL
      AND content != ''
      AND LENGTH(content) > 2
''')
print(f'有效消息数: {len(all_messages)}')

# 过滤掉纯链接、纯数字等无意义消息
def is_meaningful(content):
    content = content.strip()
    # 过滤纯链接
    if content.startswith('http'):
        return False
    # 过滤纯数字
    if content.isdigit():
        return False
    # 过滤太短的消息
    if len(content) < 3:
        return False
    return True

meaningful_msgs = [row['content'] for row in all_messages if is_meaningful(row['content'])]
print(f'有意义消息数: {len(meaningful_msgs)}')

# 定义可能的关键词类别和对应的关键词
keyword_categories = {
    "赠品/礼品": ["赠品", "礼品", "礼物", "送", "小样", "试用装", "赠", "礼盒", "包装", "袋子", "礼袋"],
    "维修保养": ["维修", "保养", "清洗", "清洁", "售后", "修理", "修", "换", "维护", "问题", "坏了", "损坏"],
    "产品规格/尺寸": ["尺寸", "大小", "口径", "规格", "多少目", "直径", "长度", "高度", "宽度", "重量", "克"],
    "价格/优惠": ["价格", "多少钱", "优惠", "折扣", "便宜", "活动", "促销", "满减", "券", "会员价"],
    "物流/发货": ["发货", "快递", "物流", "顺丰", "到货", "收到", "什么时候到", "配送", "邮寄", "运单"],
    "退换货": ["退货", "换货", "退款", "退换", "退回", "换一个", "不满意"],
    "使用咨询": ["怎么用", "如何使用", "方法", "教程", "操作", "步骤", "使用"],
    "产品推荐": ["推荐", "哪个好", "怎么选", "适合", "介绍", "有什么区别", "建议"],
    "库存/现货": ["有货", "现货", "库存", "什么时候有", "补货", "缺货", "断货"],
    "烟斗相关": ["烟斗", "斗", "斗草", "烟草", "打火机", "火机", "雪茄", "pipe", "过滤"],
    "皮具相关": ["皮带", "钱包", "皮夹", "包", "皮具", "皮革", "皮"],
    "品质/真伪": ["正品", "真假", "品质", "质量", "原装", "专柜", "官方"],
}

# 统计各类关键词出现频率
category_counts = {cat: 0 for cat in keyword_categories}
keyword_counts = Counter()

for msg in meaningful_msgs:
    for category, keywords in keyword_categories.items():
        for kw in keywords:
            if kw in msg:
                category_counts[category] += 1
                keyword_counts[kw] += 1

print("\n" + "="*60)
print("分类统计（消息数）:")
print("="*60)
for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
    pct = count / len(meaningful_msgs) * 100 if meaningful_msgs else 0
    print(f"{cat}: {count} ({pct:.1f}%)")

print("\n" + "="*60)
print("高频关键词 TOP 30:")
print("="*60)
for kw, count in keyword_counts.most_common(30):
    print(f"{kw}: {count}")

# 随机抽样一些有代表性的消息
print("\n" + "="*60)
print("代表性消息样本（包含关键词的）:")
print("="*60)

sample_queries = [
    ("赠品相关", ["赠品", "礼品", "礼物", "送", "小样"]),
    ("维修保养", ["维修", "保养", "清洗", "售后", "修理"]),
    ("产品规格", ["尺寸", "口径", "规格", "直径"]),
    ("烟斗相关", ["烟斗", "打火机", "过滤"]),
]

for label, keywords in sample_queries:
    print(f"\n--- {label} ---")
    found = 0
    for msg in meaningful_msgs:
        if any(kw in msg for kw in keywords):
            # 过滤表情符号
            clean_msg = ''.join(c for c in msg if ord(c) < 0x10000)
            print(f"  {clean_msg[:100]}")
            found += 1
            if found >= 5:
                break
