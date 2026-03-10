"""
Data Extractor - 智能提取聊天记录和订单数据的关键信息
针对奢侈品电商场景优化 - 2026-03-10
修复: 过滤客服自动回复模板，避免AI分析失败
"""
from typing import Dict, List, Any, Optional


# 新手信号关键词
ROOKIE_SIGNALS = [
    "第一次买", "新手", "小白", "不懂", "推荐", "怎么选",
    "有什么区别", "适合新手吗", "入门", "从零开始",
    "不会用", "不知道怎么", "求指导", "我是新手", "请推荐",
    "哪个好", "应该选", "不明白", "不了解", "初学者"
]

# 专家信号关键词
EXPERT_SIGNALS = [
    "具体型号", "产地", "年份", "工艺", "对比",
    "finish", "briar", "grain", "吸阻", "过滤",
    "产地工艺", "品牌历史", "具体尺寸", "参数", "材质",
    "多少目", "什么材质", "哪个品牌", "系列", "款式"
]

# 客服自动回复模板关键词（用于过滤）
AUTO_REPLY_PATTERNS = [
    "感谢您光临", "希望我们的服务给您带来愉快", "您的专属服务大使", "期待再次为您服务",
    "感谢您对dunhill的喜爱和支持", "感谢您的耐心等待",
    "请您稍等", "为您查询中", "可能会耽误几分钟",
    "多谢您对本店产品的购买", "这里也为您推荐其他您可能喜欢的商品",
    "如有需要请及时联系客服", "收到后您可以试穿查看下",
    "客服查看一下", "客服再联系", "刚刚沟通后客服"
]


def _is_auto_reply(content: str, sender: str, buyer_nick: str) -> bool:
    """
    判断是否为客服自动回复

    Args:
        content: 消息内容
        sender: 发送者昵称
        buyer_nick: 买家昵称

    Returns:
        是否为自动回复
    """
    # 如果是客户发的消息，不是自动回复
    if sender == buyer_nick:
        return False

    # 如果是客服发的，检查是否匹配自动回复模板
    for pattern in AUTO_REPLY_PATTERNS:
        if pattern in content:
            return True

    # 纯链接消息（只包含URL且很短）
    if content.strip().startswith("http") and len(content) < 100 and " " not in content.strip():
        return True

    return False


def extract_chat_insights(chats: List[Dict], buyer_nick: str = None) -> Dict[str, Any]:
    """
    智能提取聊天记录的关键信息

    Args:
        chats: 聊天记录列表
        buyer_nick: 买家昵称（用于区分客户和客服消息）

    Returns:
        {
            "完整对话": List[Dict],  # 包含所有消息（但标记自动回复）
            "客户消息": List[Dict],  # 仅保留客户的真实消息
            "新手信号": List[Dict],
            "专家信号": List[Dict],
            "问题类型": List[str]
        }
    """
    insights = {
        "完整对话": [],
        "客户消息": [],  # 新增：仅保留客户的消息
        "新手信号": [],
        "专家信号": [],
        "问题类型": []
    }

    if not chats:
        return insights

    for chat in chats:
        content = chat.get('content', '')
        sender = chat.get('sender_nick', '')
        time = chat.get('msg_time', '')

        # 判断是否为自动回复
        is_auto = _is_auto_reply(content, sender, buyer_nick) if buyer_nick else False

        # 智能截取：优先保留关键信息
        extracted_content = smart_truncate(content, max_length=500)

        # 信号检测（仅对非自动回复消息）
        if not is_auto:
            if detect_rookie_signal(content):
                insights["新手信号"].append({
                    "时间": time,
                    "内容": extracted_content,
                    "类型": identify_question_type(content)
                })

            if detect_expert_signal(content):
                insights["专家信号"].append({
                    "时间": time,
                    "内容": extracted_content,
                    "类型": identify_question_type(content)
                })

            # 识别问题类型
            question_type = identify_question_type(content)
            if question_type and question_type not in insights["问题类型"]:
                insights["问题类型"].append(question_type)

        # 完整对话（标记是否为自动回复）
        insights["完整对话"].append({
            "发送者": sender,
            "时间": time,
            "内容": extracted_content,
            "是否自动回复": is_auto
        })

        # 客户消息（仅保留非自动回复的客户消息和有价值的客服回复）
        if not is_auto:
            insights["客户消息"].append({
                "发送者": sender,
                "时间": time,
                "内容": extracted_content
            })

    return insights


def smart_truncate(text: str, max_length: int = 500) -> str:
    """
    智能截取：保留关键信息
    - 如果包含关键词，完整保留（最多1000字符）
    - 如果是长问题，保留前300 + 后200字符

    Args:
        text: 原始文本
        max_length: 最大长度

    Returns:
        截取后的文本
    """
    if not text:
        return ""

    # 关键词列表（新手问题、专业问题等）
    keywords = ["新手", "不懂", "推荐", "怎么选", "第一次", "不知道",
                "小白", "入门", "适合", "对比", "区别", "尺码", "尺寸",
                "价格", "折扣", "发货", "退换", "有问题"]

    if any(kw in text for kw in keywords):
        # 如果包含关键词且长度不超过1000，完整保留
        if len(text) <= 1000:
            return text

    if len(text) <= max_length:
        return text

    # 保留首尾，中间用...连接
    return text[:300] + "..." + text[-200:]


def detect_rookie_signal(text: str) -> bool:
    """
    检测新手信号

    Args:
        text: 聊天内容

    Returns:
        是否包含新手信号
    """
    if not text:
        return False
    return any(signal in text for signal in ROOKIE_SIGNALS)


def detect_expert_signal(text: str) -> bool:
    """
    检测专家信号

    Args:
        text: 聊天内容

    Returns:
        是否包含专家信号
    """
    if not text:
        return False
    return any(signal in text for signal in EXPERT_SIGNALS)


def identify_question_type(content: str) -> str:
    """
    识别问题类型

    Args:
        content: 聊天内容

    Returns:
        问题类型：售前咨询/使用指导/售后问题/价格询问/物流咨询/其他
    """
    if not content:
        return "其他"

    # 售前咨询
    if any(word in content for word in ["推荐", "哪个好", "怎么选", "适合", "介绍", "有什么区别", "新款", "链接"]):
        return "售前咨询"

    # 使用指导
    if any(word in content for word in ["怎么用", "如何", "不会", "不懂", "方法"]):
        return "使用指导"

    # 售后问题
    if any(word in content for word in ["坏了", "问题", "不行", "退货", "退款", "验收"]):
        return "售后问题"

    # 价格询问
    if any(word in content for word in ["多少钱", "价格", "便宜", "折扣", "优惠"]):
        return "价格询问"

    # 物流咨询
    if any(word in content for word in ["发货", "快递", "物流", "运单", "什么时候到", "顺丰"]):
        return "物流咨询"

    # 尺码咨询
    if any(word in content for word in ["尺码", "尺寸", "多大", "合身", "腰围", "胸围"]):
        return "尺码咨询"

    return "其他"


def calculate_question_style_score(chats: List[Dict]) -> Dict[str, float]:
    """
    计算问题风格分数

    Args:
        chats: 聊天记录

    Returns:
        {
            "新手分数": 0.0-1.0,
            "专家分数": 0.0-1.0,
            "疑问句密度": 0.0-1.0
        }
    """
    if not chats:
        return {"新手分数": 0.0, "专家分数": 0.0, "疑问句密度": 0.0}

    rookie_count = 0
    expert_count = 0
    question_count = 0

    for chat in chats:
        content = chat.get("content", "")

        if detect_rookie_signal(content):
            rookie_count += 1
        if detect_expert_signal(content):
            expert_count += 1
        if "？" in content or "?" in content:
            question_count += 1

    total = len(chats)

    return {
        "新手分数": rookie_count / total if total > 0 else 0.0,
        "专家分数": expert_count / total if total > 0 else 0.0,
        "疑问句密度": question_count / total if total > 0 else 0.0
    }
