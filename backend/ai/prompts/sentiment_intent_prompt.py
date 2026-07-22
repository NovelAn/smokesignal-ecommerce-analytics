"""
Sentiment and Intent Analysis Prompt
Centralized prompt template for customer message analysis
"""

INTENT_CATEGORIES = [
    "Pre-sale Inquiry",
    "Post-sale Support",
    "Logistics",
    "Usage Guide",
    "Complaint",
    "Inventory Inquiry"
]

# Thinking models may spend hundreds of tokens before emitting the JSON object.
# A 500-token cap truncates valid responses before the structured answer begins.
SENTIMENT_INTENT_MAX_TOKENS = 3000

SENTIMENT_INTENT_PROMPT = """分析以下客服对话中买家的情感和意图。

{scope_hint}

对话记录（按时间先后排列，共{message_count}条买家消息；客服消息只提供语境）:
{messages_text}

请分析并返回JSON格式结果：
{{
    "sentiment_score": 情感分数(0-1, 0=非常消极, 1=非常积极),
    "sentiment_label": "Positive"或"Neutral"或"Negative",
    "sentiment_basis": "positive_expression"或"neutral_business"或"authenticity_concern"或"explicit_complaint"或"abuse_or_threat"或"strong_negative_evaluation",
    "sentiment_evidence": "支持上述判断的买家原话；Neutral且没有情绪证据时可为空字符串",
    "intent_distribution": {{
        "Pre-sale Inquiry": 售前咨询相关消息数量,
        "Post-sale Support": 售后支持相关消息数量,
        "Logistics": 物流相关消息数量,
        "Usage Guide": 使用指南相关消息数量,
        "Complaint": 投诉相关消息数量,
        "Inventory Inquiry": 库存查询相关消息数量
    }},
    "dominant_intent": "主要意图(上述数量最多的类别)",
    "complaint_count": 投诉相关消息总数
}}

【重要】情感分数(sentiment_score)判断标准：

一、Neutral（0.4-0.6）：正常的业务咨询（最常见）
- 询问库存、价格、物流："有没有货""什么时候发货""多少钱"
- 表达疑惑或好奇："怎么下架了""就一个吗""为什么"
- 功能性请求："退款""退货""换货"
- 产品问题反馈（非投诉）："小了""大了""不合适""颜色不对""发错货"
- 商品真伪咨询、求证或怀疑："是正品吗""会不会是假货""我怀疑是假货""可以鉴定吗"
- 轻度不满、焦虑或价格遗憾："我等的很焦虑""多花二百有点难受""无语"
- 沟通摩擦或坚持观点："你怎么听不懂""我再说一遍""这不是色差"
- 正常售后沟通："好的""可以""收到"等礼貌回复
- 带语气词的询问："到底有没有啊""怎么这样"（语气词≠负面情绪）

二、Negative（< 0.4）：只有明确负面表达时才判为负面
- 明确投诉或升级行动："我要投诉""我真的会投诉你们""给差评""我要举报"
- 直接辱骂、威胁或攻击
- 对商家、商品或服务作直接且明确的强负面定性："服务太差""垃圾""你们是骗子""你们就是卖假货"

【严禁单一关键词判断】
- 不得仅因出现"假货""正品""鉴定"等词就判 Negative；必须结合问句、怀疑、客服解释和后续回应判断语义。
- 问句、求证、焦虑、难受、无语、沟通摩擦、反复坚持观点都不等于投诉或强负面定性。
- "虚假宣传吗"是询问或质疑，不是明确投诉；只有"你们就是虚假宣传，我要投诉"才达到 Negative 门槛。
- 多个未达到 Negative 门槛的表达不能累加升级；必须存在至少一句买家原话单独达到上述门槛。
- "我怀疑是假货"是要求核实真伪，sentiment_basis=authenticity_concern，默认 Neutral。
- "你们就是卖假货"是明确负面定性，sentiment_basis=strong_negative_evaluation，可判 Negative。
- 只有 explicit_complaint / abuse_or_threat / strong_negative_evaluation 可以对应 Negative。
- 客服消息只用于理解语境、解释和问题处理情况；情感、意图数量及证据只取买家消息。

三、Positive（> 0.6）：明确的正面情绪
- 表达感谢、满意、赞赏
- 再次购买意愿、推荐他人

【重要】意图分类标准（每条买家消息必须归入以下6类之一）：

1. Pre-sale Inquiry（售前咨询）- 询问产品、价格、推荐、款式等购买前问题（排除单纯库存查询）
   - 关键词：推荐、多少钱、尺寸、颜色、款式、新款、上市、材质、面料、有没有、现货
   - ✅ "推荐一款春季外套" → Pre-sale Inquiry
   - ✅ "这个有没有L码" → Pre-sale Inquiry
   - ✅ "新款什么时候上架" → Pre-sale Inquiry
   - ✅ "这件和那件有什么区别" → Pre-sale Inquiry
   - ✅ "这个还有货吗" → Pre-sale Inquiry（单纯库存确认，非缺货/补货诉求）
   - ✅ "是现货吗" → Pre-sale Inquiry（库存确认）

2. Post-sale Support（售后支持）- 收到产品后的问题反馈、退换货咨询、保修维修
   - 关键词：退货、换货、退款、小了、大了、不合适、颜色不对、发错货、质量问题
   - ✅ "小了，我要退货" → Post-sale Support
   - ✅ "发错货了，帮我换一下" → Post-sale Support
   - ✅ "收到货了，颜色和图片不一样" → Post-sale Support

3. Logistics（物流）- 关于发货、快递、物流跟踪、配送时间
   - 关键词：发货、快递、物流、什么时候到、运费、地址
   - ✅ "什么时候发货" → Logistics
   - ✅ "快递到哪了" → Logistics

4. Usage Guide（使用指南）- 询问如何使用、保养、功能说明
   - 关键词：怎么用、怎么保养、清洗、收纳
   - ✅ "这个皮具怎么保养" → Usage Guide

5. Complaint（投诉）- 仅限明确投诉行为（非常严格）
   - 强投诉词：投诉/差评/举报/315/消费者协会/工商/找经理
   - 负面评价词：太差/质量差/很差/垃圾/骗子/假货/欺骗/失望/不满/态度差/服务差
   - ❌ 单纯退换货不算投诉，❌ 语气词不算不满，❌ 询问不算投诉

6. Inventory Inquiry（库存需求）- 客户表达**缺货/补货/调货**诉求：已知或疑心没货，问何时补货、能否调货、还会不会上架
   - 关键词（作为主要意图）：没货、断货、缺货、补货、没现货、什么时候补货、什么时候有货、还会上架吗
   - 判断依据：
     * 客户已知缺货或担心缺货，带有明确的补货/调货/恢复购买诉求
     * 单纯的"有没有货/是现货吗"库存确认**不算**（客户只是下单前确认，无缺货诉求）→ 归 Pre-sale Inquiry
     * 客服自动回复/快捷短语（如"X年生肖X现货"）**不算**
   - ✅ "这个41没货了，什么时候补货" → Inventory Inquiry
   - ✅ "缺货了吗，还能买到吗" → Inventory Inquiry
   - ✅ "能帮补货39码吗" → Inventory Inquiry
   - ✅ "下个月会补货吗" → Inventory Inquiry
   - ❌ "这个还有货吗" → Pre-sale Inquiry（单纯库存确认，无缺货/补货诉求）
   - ❌ "是现货吗 / 有没有现货" → Pre-sale Inquiry（库存确认）
   - ❌ "2026马年生肖烟斗现货" → Pre-sale Inquiry（客服自动回复/快捷短语，非客户咨询）
   - ❌ "推荐一个有货的款" → Pre-sale Inquiry（核心是推荐）

【重要】intent_distribution 的数值 = 属于该类别的消息条数（不是分数），所有类别的数值之和应等于消息总数。

【示例】：
- "推荐一款春季外套" → Neutral(0.5), Pre-sale Inquiry
- "这个还有货吗" → Neutral(0.5), Pre-sale Inquiry（库存确认，非缺货诉求）
- "是现货吗" → Neutral(0.5), Pre-sale Inquiry（库存确认）
- "41没货了，什么时候补货" → Neutral(0.5), Inventory Inquiry（缺货+补货诉求）
- "能帮补货39码吗" → Neutral(0.5), Inventory Inquiry
- "2026马年生肖烟斗现货" → Neutral(0.5), Pre-sale Inquiry（客服自动回复）
- "质量太差了" → Negative(0.2), Complaint
- "我要投诉你们" → Negative(0.2), Complaint
- "小了，我要退货" → Neutral(0.5), Post-sale Support（正常退货≠投诉）
- "发错货了，帮我换一下" → Neutral(0.5), Post-sale Support（正常售后≠投诉）
- "我怀疑是假货，可以核实吗" → Neutral(0.5), Post-sale Support，authenticity_concern
- "如果你管这叫金色，那我就申请鉴定；我再说一遍，这不是色差" → Neutral(0.45), Post-sale Support，authenticity_concern
- "你怎么听不懂；虚假宣传吗；无语" → Neutral(0.4), Post-sale Support（沟通摩擦和反问不等于投诉）
- "同样的东西多花二百有点难受；我等的很焦虑" → Neutral(0.4), Pre-sale Inquiry
- "你们就是卖假货，我要举报" → Negative(0.2), Complaint，explicit_complaint
- "什么时候发货" → Neutral(0.5), Logistics
- "好的👌" → Neutral(0.6), Post-sale Support（礼貌确认）

只返回JSON，不要其他内容。"""


def build_sentiment_intent_prompt(
    messages: list[str],
    is_incremental: bool = False
) -> str:
    """
    Build sentiment and intent analysis prompt

    Args:
        messages: List of customer messages
        is_incremental: True if analyzing only new messages since last analysis

    Returns:
        Formatted prompt string
    """
    scope_hint = (
        "以下是**自上次分析以来的新增聊天**（请仅基于以下新增聊天判断情感和意图，不要考虑之前的历史聊天）。"
        if is_incremental
        else "以下是买家的全部历史聊天（请基于全部历史聊天判断每条消息的情感和意图）。"
    )

    has_dialogue_roles = any(
        str(message).startswith(("[买家]", "[客服]"))
        for message in messages
    )
    if has_dialogue_roles:
        selected_messages = messages
        message_count = sum(
            str(message).startswith("[买家]") for message in selected_messages
        )
        messages_text = "\n".join(str(message) for message in selected_messages)
    else:
        selected_messages = messages[:20]
        message_count = len(selected_messages)
        messages_text = "\n".join(f"[买家] {message}" for message in selected_messages)

    return SENTIMENT_INTENT_PROMPT.format(
        scope_hint=scope_hint,
        message_count=message_count,
        messages_text=messages_text
    )
