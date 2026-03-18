"""
Domain Knowledge - 烟斗/烟具领域专业知识
用于AI分析时注入领域知识，提升分析准确性
"""

# 烟斗品类专业知识
PIPE_CATEGORIES = {
    "PIPES": {
        "name": "烟斗",
        "expert_signals": [
            "finish", "briar", "grain", "吸阻", "斗钵",
            "斗柄", "滤芯", "石楠木", "海泡石", "玉米斗",
            "system", "lovat", "billiard", "pot", "bent", "straight"
        ],
        "rookie_signals": [
            "新手", "推荐", "怎么选", "第一次", "入门",
            "哪个好", "不懂", "求推荐", "适合新手"
        ],
        "care_products": [
            "通条", "压棒", "清洁工具", "斗架", "防风打火机",
            "烟草罐", "保湿盒", "烟草袋"
        ],
        "related_categories": ["LIGHTERS", "TOBACCO", "JEWELLERY"],
        "expert_questions": [
            "这个石楠木的产地是哪里？",
            "吸阻多少？",
            "斗钵厚度多少？",
            "有没有滤芯？"
        ],
        "rookie_questions": [
            "新手用哪个好？",
            "怎么选烟斗？",
            "烟斗怎么用？",
            "推荐一个入门的"
        ]
    },

    "LIGHTER": {
        "name": "打火机",
        "expert_signals": [
            "直冲", "软火", "喷枪", "Zippo", "帕克",
            "双火焰", "三火焰", "可调火", "防风", "气压"
        ],
        "rookie_signals": [
            "新手", "推荐", "第一次买", "不懂",
            "哪个好用", "怎么用"
        ],
        "care_products": [
            "火机油", "气", "棉芯", "火石"
        ],
        "related_categories": ["PIPES", "JEWELLERY"],
        "expert_questions": [
            "这是什么型号？",
            "火焰温度多少？",
            "一次能用多久？"
        ],
        "rookie_questions": [
            "怎么加油？",
            "怎么点火？",
            "推荐一个打火机"
        ]
    },

    "TOBACCO": {
        "name": "烟草",
        "expert_signals": [
            "V", "Virginia", "Burley", "Cavendish", "Latakia",
            "Perique", "English", "Aromatic", "Virginia",
            "切片", "丝状", "颗粒", "拧绳", "板烟"
        ],
        "rookie_signals": [
            "新手", "推荐", "淡一点", "浓一点",
            "哪个好抽", "第一次抽"
        ],
        "care_products": [
            "烟草罐", "保湿盒", "保湿袋", "密封罐"
        ],
        "related_categories": ["PIPES", "LIGHTERS"],
        "expert_questions": [
            "这是什么配方？",
            "V比例多少？",
            "有没有Latakia？",
            "醇化几年？"
        ],
        "rookie_questions": [
            "新手抽哪个？",
            "推荐一个淡的",
            "怎么储存？"
        ]
    },

    "JEWELLERY": {
        "name": "烟嘴/配件",
        "expert_signals": [
            "琥珀", "象牙", "金属", "亚克力", "胶木",
            "滤芯", "弯度", "口径", "冷却效果"
        ],
        "rookie_signals": [
            "推荐", "哪个好", "新手用",
            "怎么选", "第一次买"
        ],
        "related_categories": ["PIPES", "LIGHTERS"],
        "expert_questions": [
            "什么材质？",
            "口径多少？",
            "有没有滤芯？",
            "弯度多少？"
        ],
        "rookie_questions": [
            "烟嘴怎么用？",
            "推荐一个烟嘴",
            "哪个好？"
        ]
    }
}

# 价格区间判断
PRICE_RANGES = {
    "PIPES": {
        "入门": (0, 200),
        "中级": (200, 800),
        "高级": (800, 2000),
        "专家": (2000, 100000)
    },
    "LIGHTER": {
        "入门": (0, 100),
        "中级": (100, 300),
        "高级": (300, 1000),
        "专家": (1000, 100000)
    },
    "TOBACCO": {
        "入门": (0, 50),
        "中级": (50, 150),
        "高级": (150, 500),
        "专家": (500, 100000)
    }
}

# 购买行为模式
BUYING_PATTERNS = {
    "收藏家": {
        "signals": ["购买高端产品", "购买限量版", "购买不同款式"],
        "recommendation": "推荐限量版、高端新品"
    },
    "使用者": {
        "signals": ["购买消耗品", "重复购买同类产品", "购买配件"],
        "recommendation": "推荐消耗品、配件、促销装"
    },
    "送礼者": {
        "signals": ["购买礼盒装", "购买中高端产品", "节日购买"],
        "recommendation": "推荐礼盒装、高端礼品"
    },
    "尝鲜者": {
        "signals": ["购买不同品类", "购买入门产品", "购买多样化"],
        "recommendation": "推荐新品、套装、试用装"
    }
}

# 客户生命周期阶段
LIFECYCLE_STAGES = {
    "新手": {
        "特征": ["购买入门产品", "询问基础问题", "购买频次低"],
        "推荐策略": "推荐入门套装、教程、新手指南"
    },
    "成长期": {
        "特征": ["购买频次增加", "尝试不同品类", "开始购买配件"],
        "推荐策略": "推荐中级产品、配件、组合优惠"
    },
    "成熟期": {
        "特征": ["购买稳定", "有明确偏好", "购买高端产品"],
        "推荐策略": "推荐高端产品、限量版、个性化定制"
    },
    "专家": {
        "特征": ["购买高端产品", "专业知识强", "收藏行为"],
        "推荐策略": "推荐限量版、稀缺品、新品首发"
    }
}


def get_category_knowledge(category: str) -> dict:
    """
    获取特定品类的专业知识

    Args:
        category: 品类名称（如 "PIPES", "LIGHTER"）

    Returns:
        品类知识字典
    """
    return PIPE_CATEGORIES.get(category, {})


def detect_customer_level(chats: list, orders: list, profile: dict) -> str:
    """
    检测客户水平（新手/成长期/成熟期/专家）

    Args:
        chats: 聊天记录
        orders: 订单记录
        profile: 客户档案

    Returns:
        客户水平
    """
    # 检查聊天中的新手信号
    rookie_count = 0
    expert_count = 0

    for chat in chats:
        content = chat.get("content", "")
        # 简单统计新手/专家关键词
        for category_data in PIPE_CATEGORIES.values():
            for signal in category_data.get("rookie_signals", []):
                if signal in content:
                    rookie_count += 1
            for signal in category_data.get("expert_signals", []):
                if signal in content:
                    expert_count += 1

    # 检查消费水平
    avg_order_value = profile.get("l6m_netsales", 0) / max(profile.get("l6m_orders", 1), 1)

    # 综合判断
    if expert_count > rookie_count and avg_order_value > 500:
        return "专家"
    elif expert_count > 0 or avg_order_value > 300:
        return "成熟期"
    elif rookie_count > 0 or avg_order_value > 100:
        return "成长期"
    else:
        return "新手"


def generate_recommendations(
    top_category: str,
    customer_level: str,
    profile: dict
) -> list:
    """
    生成个性化推荐

    Args:
        top_category: 主要购买品类
        customer_level: 客户水平
        profile: 客户档案

    Returns:
        推荐商品/品类列表
    """
    recommendations = []

    # 基于品类推荐
    category_data = get_category_knowledge(top_category)
    if category_data:
        # 推荐相关品类
        for related_cat in category_data.get("related_categories", []):
            related_data = get_category_knowledge(related_cat)
            if related_data:
                recommendations.append(f"{related_data['name']}")

        # 推荐配件
        for product in category_data.get("care_products", []):
            recommendations.append(product)

    # 基于客户水平推荐
    lifecycle_data = LIFECYCLE_STAGES.get(customer_level, {})
    if lifecycle_data:
        rec_strategy = lifecycle_data.get("推荐策略", "")
        recommendations.append(rec_strategy)

    return list(set(recommendations))  # 去重


def inject_domain_knowledge_to_prompt(
    prompt: str,
    top_category: str,
    profile: dict
) -> str:
    """
    将领域知识注入到prompt中

    Args:
        prompt: 原始prompt
        top_category: 主要品类
        profile: 客户档案

    Returns:
        增强后的prompt
    """
    category_knowledge = get_category_knowledge(top_category)

    if not category_knowledge:
        return prompt

    # 构建领域知识描述
    knowledge_section = f"""

【领域知识 - {category_knowledge.get('name', top_category)}】

专家信号关键词：{', '.join(category_knowledge.get('expert_signals', [])[:10])}
新手信号关键词：{', '.join(category_knowledge.get('rookie_signals', [])[:10])}
相关品类：{', '.join(category_knowledge.get('related_categories', []))}
配件推荐：{', '.join(category_knowledge.get('care_products', [])[:10])}

在分析时，请结合以上领域知识判断客户的专业水平。
"""

    # 将领域知识插入到prompt中
    return prompt + knowledge_section


def build_external_info_context(external_records: list) -> str:
    """
    构建场外信息上下文

    将场外记录格式化为 AI 可理解的文本，用于补充客户画像分析

    Args:
        external_records: 场外记录列表，每条记录包含:
            - record_type: 'communication' | 'purchase'
            - record_date: 日期字符串
            - channel: 渠道/门店
            - content: 内容描述
            - amount: 消费金额（仅消费类型）
            - category: 商品品类（仅消费类型）
            - notes: 备注

    Returns:
        格式化的场外信息文本
    """
    if not external_records:
        return ""

    context_lines = []

    # 分组：沟通记录和消费记录
    communications = [r for r in external_records if r.get('record_type') == 'communication']
    purchases = [r for r in external_records if r.get('record_type') == 'purchase']

    # 线下消费记录
    if purchases:
        context_lines.append("\n【线下门店消费记录（不计入线上统计）】")
        total_amount = 0
        for record in purchases:
            date = record.get('record_date', '未知日期')
            channel = record.get('channel', '未知门店')
            amount = float(record.get('amount') or 0)
            category = record.get('category', '')
            notes = record.get('notes', '')

            total_amount += amount
            line = f"- [{date}] {channel}"
            if amount > 0:
                line += f" 消费 ¥{amount:,.0f}"
            if category:
                line += f" ({category})"
            if notes:
                line += f" - {notes}"
            context_lines.append(line)

        if total_amount > 0:
            context_lines.append(f"  线下消费小计: ¥{total_amount:,.0f}")

    # 私域沟通记录
    if communications:
        context_lines.append("\n【私域沟通记录（微信/电话等）】")
        for record in communications:
            date = record.get('record_date', '未知日期')
            channel = record.get('channel', '未知渠道')
            content = record.get('content', '')
            notes = record.get('notes', '')

            line = f"- [{date}] {channel}"
            if content:
                # 截取前100字符避免过长
                content_preview = content[:100] + ('...' if len(content) > 100 else '')
                line += f": {content_preview}"
            if notes:
                line += f" [备注: {notes}]"
            context_lines.append(line)

    return '\n'.join(context_lines)


def build_customer_context_with_external(
    profile: dict,
    external_records: list = None
) -> str:
    """
    构建完整的客户上下文（包含场外信息）

    用于 AI 分析时提供完整的客户背景信息

    Args:
        profile: 客户档案数据
        external_records: 场外记录列表（可选）

    Returns:
        格式化的客户上下文文本
    """
    user_nick = profile.get('user_nick') or profile.get('buyer_nick', '未知客户')

    context = f"""
## 客户基本信息
- 昵称: {user_nick}
- 城市: {profile.get('city', '未知')}
- 渠道: {profile.get('channel', '未知')}
- 客户类型: {profile.get('buyer_type', '未知')}
- VIP等级: {profile.get('vip_level', 'Non-VIP')}
- 新老客户: {'新客户' if profile.get('client_monthly_tag') == 'new' else '老客户'}

## 线上消费数据（Dashboard统计来源）
- 历史总消费: ¥{profile.get('historical_net_sales', 0):,.0f}
- 历史订单数: {profile.get('total_orders', 0)}
- 近6个月消费: ¥{profile.get('l6m_netsales', 0):,.0f}
- 近6个月订单: {profile.get('l6m_orders', 0)}
- 退款率: {profile.get('refund_rate', 0):.1%}

## 行为特征
- 折扣敏感度: {profile.get('discount_sensitivity', '未知')}
- 流失风险: {profile.get('churn_risk', '未知')}
- 首次购买: {profile.get('first_purchase_date', '未知')}
- 最近购买: {profile.get('last_purchase_date', '未知')}

## 品类偏好
- 首要品类: {profile.get('top_category', '未知')}
- 次要品类: {profile.get('second_category', '-')}
- 第三品类: {profile.get('third_category', '-')}
"""

    # 添加聊天行为
    chat_freq = profile.get('chat_frequency_days', 0)
    last_chat = profile.get('last_chat_date')
    if chat_freq > 0 or last_chat:
        context += f"""
## 沟通行为
- 沟通频率: 每{chat_freq}天一次
- 最近沟通: {last_chat or '无记录'}
"""

    # 添加场外信息（如果存在）
    if external_records:
        external_context = build_external_info_context(external_records)
        if external_context:
            context += f"""
## 场外补充信息（仅供参考，不计入线上统计）
{external_context}
"""
    else:
        context += """
## 场外补充信息
- 暂无场外信息记录
"""

    return context


# 示例使用
if __name__ == "__main__":
    # 获取烟斗品类知识
    pipe_knowledge = get_category_knowledge("PIPES")
    print(f"烟斗品类知识: {pipe_knowledge['name']}")

    # 检测客户水平
    profile = {
        "l6m_netsales": 5000,
        "l6m_orders": 10
    }
    level = detect_customer_level(
        chats=[{"content": "这个finish怎么样"}],
        orders=[],
        profile=profile
    )
    print(f"客户水平: {level}")

    # 生成推荐
    recs = generate_recommendations("PIPES", "成熟期", profile)
    print(f"推荐: {recs}")
