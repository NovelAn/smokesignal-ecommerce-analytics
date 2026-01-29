"""
Data Extractor - 智能提取聊天记录和订单数据的关键信息
"""
from typing import Dict, List, Any


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


def extract_chat_insights(chats: List[Dict]) -> Dict[str, Any]:
    """
    智能提取聊天记录的关键信息

    Args:
        chats: 聊天记录列表

    Returns:
        {
            "完整对话": List[Dict],
            "新手信号": List[Dict],
            "专家信号": List[Dict],
            "问题类型": List[str]
        }
    """
    insights = {
        "完整对话": [],
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

        # 智能截取：优先保留关键信息
        extracted_content = smart_truncate(content, max_length=500)

        # 信号检测
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

        insights["完整对话"].append({
            "发送者": sender,
            "时间": time,
            "内容": extracted_content
        })

    return insights


def smart_truncate(text: str, max_length: int = 500) -> str:
    """
    智能截取：保留关键信息
    - 如果包含关键词，完整保留
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
                "不懂", "小白", "入门", "适合", "对比", "区别"]

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
    if any(word in content for word in ["推荐", "哪个好", "怎么选", "适合", "介绍", "有什么区别"]):
        return "售前咨询"

    # 使用指导
    if any(word in content for word in ["怎么用", "如何", "不会", "不懂", "方法"]):
        return "使用指导"

    # 售后问题
    if any(word in content for word in ["坏了", "问题", "不行", "退货", "退款"]):
        return "售后问题"

    # 价格询问
    if any(word in content for word in ["多少钱", "价格", "便宜", "折扣", "优惠"]):
        return "价格询问"

    # 物流咨询
    if any(word in content for word in ["发货", "快递", "物流", "运单", "什么时候到"]):
        return "物流咨询"

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
