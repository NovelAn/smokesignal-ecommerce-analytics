"""Shared persona context and prompt builders.

All persona analysis entry points and model providers should use this module for
business facts and prompt wording. Provider-specific code should only decide
model, temperature, token limits, and transport details.
"""
import json
from typing import Any, Dict, List

from backend.ai.behavior_analyzer import build_order_facts, structure_order_behavior
from backend.ai.data_extractor import extract_chat_insights
from backend.ai.prompts.domain_knowledge import build_external_info_context


def build_persona_profile_data(
    buyer_nick: str,
    profile: Dict[str, Any],
    chats: List[Dict[str, Any]] | None = None,
    external_records: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """Normalize buyer profile fields used by persona analysis."""
    from datetime import datetime as dt

    chats = chats or []
    external_records = external_records or []
    today = dt.now()

    def as_float(key: str, default: float = 0.0) -> float:
        try:
            return float(profile.get(key, default) or default)
        except (TypeError, ValueError):
            return default

    def as_int(key: str, default: int = 0) -> int:
        try:
            return int(float(profile.get(key, default) or default))
        except (TypeError, ValueError):
            return default

    def parse_date(value: Any):
        if not value:
            return None
        if hasattr(value, "year"):
            return value
        text = str(value)
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return dt.strptime(text[:len(fmt)], fmt)
            except ValueError:
                continue
        return None

    first_purchase_date = parse_date(profile.get("first_purchase_date"))
    last_purchase_date = parse_date(profile.get("last_purchase_date"))
    last_chat_date = parse_date(profile.get("last_chat_date"))
    total_orders = as_int("total_orders")

    days_since_last_purchase = (today - last_purchase_date).days if last_purchase_date else 0
    days_since_last_chat = (today - last_chat_date).days if last_chat_date else 0
    avg_repurchase_interval_days = 0
    if first_purchase_date and last_purchase_date and total_orders > 1:
        days_span = (last_purchase_date - first_purchase_date).days
        avg_repurchase_interval_days = round(days_span / (total_orders - 1)) if days_span > 0 else 0

    return {
        "user_nick": buyer_nick,
        "buyer_nick": profile.get("buyer_nick") or buyer_nick,
        "channel": profile.get("channel"),
        "buyer_type": profile.get("buyer_type"),
        "is_smoker": profile.get("is_smoker", 0),
        "is_vic": profile.get("is_vic", 0),
        "vip_level": profile.get("vip_level", "Non-VIP"),
        "client_monthly_tag": profile.get("client_monthly_tag"),
        "city": profile.get("city", "Unknown"),
        "historical_gmv": as_float("historical_gmv"),
        "historical_refund": as_float("historical_refund"),
        "historical_net_sales": as_float("historical_net_sales"),
        "total_orders": total_orders,
        "total_net_orders": as_int("total_net_orders"),
        "refund_rate": as_float("refund_rate"),
        "first_purchase_date": str(profile.get("first_purchase_date", "") or ""),
        "last_purchase_date": str(profile.get("last_purchase_date", "") or ""),
        "first_chat_date": str(profile.get("first_chat_date")) if profile.get("first_chat_date") else None,
        "last_chat_date": str(profile.get("last_chat_date")) if profile.get("last_chat_date") else None,
        "days_since_last_purchase": days_since_last_purchase,
        "days_since_last_chat": days_since_last_chat,
        "avg_repurchase_interval_days": avg_repurchase_interval_days,
        "rolling_24m_netsales": as_float("rolling_24m_netsales"),
        "rolling_24m_orders": as_int("rolling_24m_orders"),
        "l6m_gmv": as_float("l6m_gmv"),
        "l6m_netsales": as_float("l6m_netsales"),
        "l6m_orders": as_int("l6m_orders"),
        "l6m_refund_rate": as_float("l6m_refund_rate"),
        "l1y_gmv": as_float("l1y_gmv"),
        "l1y_netsales": as_float("l1y_netsales"),
        "l1y_orders": as_int("l1y_orders"),
        "l1y_refund_rate": as_float("l1y_refund_rate"),
        "discount_ratio": as_float("discount_ratio"),
        "discount_sensitivity": profile.get("discount_sensitivity", "未知"),
        "chat_frequency_days": as_int("chat_frequency_days"),
        "l30d_chat_frequency_days": as_int("l30d_chat_frequency_days"),
        "l3m_chat_frequency_days": as_int("l3m_chat_frequency_days"),
        "avg_chat_interval_days": as_float("avg_chat_interval_days"),
        "churn_risk": profile.get("churn_risk", "未知"),
        "top_category": profile.get("top_category", "Unknown"),
        "second_category": profile.get("second_category"),
        "third_category": profile.get("third_category"),
        "chat_history": chats,
        "external_records": external_records,
        "total_refund_count": as_int("total_refund_count"),
    }


def build_persona_context(
    buyer_nick: str,
    profile: Dict[str, Any],
    chats: List[Dict[str, Any]],
    orders: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build the shared facts all persona models receive."""
    chats = chats or []
    orders = orders or []
    external_records = profile.get("external_records", []) or []
    return {
        "buyer_nick": buyer_nick,
        "profile": profile,
        "order_facts": build_order_facts(profile, orders, top_n=12),
        "order_behavior": structure_order_behavior(profile, orders),
        "chat_insights": extract_chat_insights(chats, buyer_nick),
        "recent_chats": chats[:20],
        "external_info": build_external_info_context(external_records) if external_records else "暂无场外信息记录",
    }


def build_persona_prompt(
    buyer_nick: str,
    profile: Dict[str, Any],
    chats: List[Dict[str, Any]],
    orders: List[Dict[str, Any]],
) -> str:
    """Build the single shared business prompt for all LLM persona providers."""
    context = build_persona_context(buyer_nick, profile, chats, orders)
    compact_context = {
        "buyer_nick": buyer_nick,
        "profile": {
            key: context["profile"].get(key)
            for key in [
                "vip_level", "buyer_type", "client_monthly_tag",
                "total_orders", "historical_gmv", "historical_net_sales",
                "discount_ratio", "discount_sensitivity",
                "days_since_last_purchase", "days_since_last_chat",
                "avg_repurchase_interval_days", "top_category",
                "second_category", "third_category",
            ]
        },
        "order_facts": context["order_facts"],
        "order_behavior": context["order_behavior"],
        "chat_insights": context["chat_insights"],
        "external_info": context["external_info"],
    }

    return f"""
你是一位电商客户洞察专家，负责基于真实数据生成 dunhill 客户画像。

所有模型、所有入口（详情页、force refresh、batch）都必须使用同一套业务标准：
1. 只基于下方事实，不编造数字。
2. 订单总数、AOV、MD/折扣占比、品类占比、购买高峰必须以 facts 中数字为准。
3. summary 不要流水账，不要逐单复述，必须提炼客户关键特征。
4. 必须覆盖三类判断：购买时间习惯、品类偏好、价格/折扣心智。
5. 大促窗口定义：5-6 月视为 618/季末节点，10-12 月视为双11/双12/冬季特惠节点。
6. 折扣占比低但购买集中在大促窗口时，应判断为“固定在平台大促/季末节点集中购买”，不要写成“对折扣完全无感”。
7. 多个品类并存时，不允许把最高频品类写成全部订单；外套、Polo、T恤、针织等应归纳为男士上装/成衣偏好。

【统一事实上下文】
{json.dumps(compact_context, ensure_ascii=False, indent=2, default=str)[:7000]}

请只返回合法 JSON，不要 Markdown，不要解释过程：
{{
  "summary": "2-3句话，提炼客户关键特征，包含购买时间习惯、品类偏好、价格/折扣心智",
  "key_interests": ["3-5个稳定偏好或行为习惯"],
  "pain_points": ["2-4个真实可见的阻碍、风险或转化弱点"],
  "recommended_action": "1-2句话，说明下一步触达时机、推荐品类和销售动作",
  "confidence_level": "高/中/低"
}}
"""


def build_persona_prompt_v2(
    buyer_nick: str,
    profile: Dict[str, Any],
    chats: List[Dict[str, Any]],
    orders: List[Dict[str, Any]],
) -> str:
    """Build a less templated prompt that emphasizes chat-driven insight."""
    context = build_persona_context(buyer_nick, profile, chats, orders)
    compact_context = {
        "buyer_nick": buyer_nick,
        "profile": {
            key: context["profile"].get(key)
            for key in [
                "vip_level", "buyer_type", "client_monthly_tag",
                "total_orders", "historical_gmv", "historical_net_sales",
                "discount_ratio", "discount_sensitivity",
                "days_since_last_purchase", "days_since_last_chat",
                "avg_repurchase_interval_days", "top_category",
                "second_category", "third_category",
            ]
        },
        "order_facts": context["order_facts"],
        "order_behavior": context["order_behavior"],
        "chat_insights": context["chat_insights"],
        "recent_chats": context["recent_chats"],
        "external_info": context["external_info"],
    }

    return f"""
你是 dunhill 电商客户洞察专家。目标不是套模板汇总数字，而是结合【聊天记录 + 销售订单】提炼客户的真实偏好、顾虑、运营机会。

业务原则：
1. 只基于下方事实，不编造数字；订单总数、AOV、MD/折扣占比、品类占比、购买高峰必须以 facts 为准。
2. summary 不要使用固定句式，不要以“历史xx单，AOV...”开头套模板；只有当这些数字能支持一个客户特征时才写。
3. 必须优先阅读 chat_insights/recent_chats，把聊天中体现的关注点、顾虑、决策方式、沟通风格写进画像。
4. 订单数据用于解释客户行为：购买时间习惯、品类偏好、价格/折扣心智、复购节奏、召回窗口。
5. 大促窗口定义：5-6 月为 618/季末节点，10-12 月为双11/双12/冬季特惠节点。
6. 折扣占比低但购买集中在大促窗口时，应判断为“固定在平台大促/季末节点集中购买”，不要写成“对折扣完全无感”。
7. 多个品类并存时，不能把最高频品类写成全部订单；外套、Polo、T恤、针织等应归纳为男士上装/成衣偏好。

分析任务：
- summary：用2-3句话写“这个客户是什么样的人、为什么这样判断、后续怎么触达更有效”。必须融合聊天和订单两类证据。
- key_interests：写客户稳定偏好，包括商品/品类、购买时机、沟通中明确关注的点。
- pain_points：写需要解决或提升的点，比如尺码/搭配顾虑、价格等待、活动依赖、沟通沉默、跨品类扩展弱等。
- recommended_action：给出具体运营动作，包含触达时机、话术方向、推荐品类/商品方向。

不要输出：
- 纯数字流水账
- 只改数字的模板句
- “高端正价客户”“对折扣完全无感”这类没有充分证据的标签
- 页面已展示的基础信息

【统一事实上下文】
{json.dumps(compact_context, ensure_ascii=False, indent=2, default=str)[:9000]}

只返回合法 JSON，不要 Markdown，不要解释过程：
{{
  "summary": "2-3句话，融合聊天和订单证据，提炼客户关键特征",
  "key_interests": ["3-5个稳定偏好/行为习惯/聊天关注点"],
  "pain_points": ["2-4个需要解决或提升的点"],
  "recommended_action": "具体触达时机、话术方向、推荐品类/商品方向",
  "confidence_level": "高/中/低"
}}
"""


def build_persona_prompt_v3(
    buyer_nick: str,
    profile: Dict[str, Any],
    chats: List[Dict[str, Any]],
    orders: List[Dict[str, Any]],
    is_incremental: bool = False,
) -> str:
    """Build the shared v3 persona prompt for all persona providers.

    Args:
        is_incremental: True 表示 chats 仅含"自上次分析以来的新增部分 + 少量历史上下文"
                       (Round 4 增量优化), prompt 会提示 LLM "不要推翻核心画像"
    """
    scope_hint = ''
    if is_incremental:
        scope_hint = (
            '【增量分析说明】以下聊天记录是自上次画像分析以来的**新增部分** + 5 条历史上下文（按时间倒序，最新在前）。\n'
            '请只基于这部分新聊天更新客户画像的演进趋势（关注点变化、决策风格变化、新增痛点、情绪走向），\n'
            '**不要推翻**已经稳定的核心画像特征。\n\n'
        )
    # R5: 复购频率预计算 — 后端算好, LLM 看到数值直接引用, 禁止自己算
    _interval = profile.get("avg_repurchase_interval_days")
    _total_orders = profile.get("total_orders") or 0
    if _total_orders <= 1 or not _interval or _interval <= 0:
        _repurchase_freq = "首次购买或数据不足"
    elif _interval < 60:
        _repurchase_freq = f"高频（约{_interval:.0f}天/单）"
    elif _interval < 180:
        _repurchase_freq = f"中频（约{_interval:.0f}天/单）"
    elif _interval < 365:
        _repurchase_freq = f"中低频（约{_interval:.0f}天/单）"
    else:
        _repurchase_freq = f"低频（约{_interval:.0f}天/单）"

    context = build_persona_context(buyer_nick, profile, chats, orders)
    compact_context = {
        "buyer_nick": buyer_nick,
        "repurchase_frequency": _repurchase_freq,  # R5 预计算, LLM 直接读
        # ⚠️ JSON 顺序 = 截断优先级 (json.dumps 从前往后, 6000 字符后截断)
        # chat 数据必须在 order 前面: 6000 字符内优先保留聊天洞察 + 最近对话
        "chat_insights": context["chat_insights"],
        "recent_chats": context["recent_chats"],
        "order_facts": context["order_facts"],
        "order_behavior": context["order_behavior"],
        "profile": {
            key: context["profile"].get(key)
            for key in [
                # 销售核心 (3) — 24m 是 VIP 等级依据
                "rolling_24m_netsales",
                "l6m_netsales",
                "l1y_netsales",
                # 时间 (3) — 后端算好, LLM 不准自己算
                "last_purchase_date",
                "days_since_last_purchase",
                "avg_repurchase_interval_days",
                # 退款 (1) — 质量硬信号
                "refund_rate",
                # 订单 (1) — 复购频次分母
                "total_orders",
                # 折扣 (2)
                "discount_ratio",
                "discount_sensitivity",
                # 品类 (3) — 画像核心输出
                "top_category", "second_category", "third_category",
                # 风险 (1)
                "churn_risk",
            ]
        },
    }

    return scope_hint + f"""
你是 dunhill 电商客户洞察专家。你的任务不是复述订单数字，而是基于同一套真实数据，提炼客户的关键特征、购买偏好、顾虑痛点和后续运营机会。

【复购频率已预计算】{_repurchase_freq}
- summary 必含 "复购频率：{_repurchase_freq}" 字段


统一规则：
1. 所有结论只能来自下方 JSON 事实包，不能编造数字、商品、聊天内容或退货原因。
2. 订单总数、AOV、GMV/净销售、MD/折扣占比、品类占比、退款、购买高峰必须以 order_facts/profile 为准。
3. 所有入口和模型都使用这套规则；DeepSeek、MiniMax、force refresh、batch、详情页更新不能有不同业务逻辑。
4. 必须同时分析订单和聊天。若有聊天记录，必须提炼聊天中体现的关注点、顾虑、痛点、退货/换货原因、决策风格、沟通风格；若聊天证据不足，明确写"聊天证据不足"，不要编。
5. 购买时间判断必须单独写清：5-6 月视为 618/季末节点，10-12 月视为双11/双12/冬季特惠节点。需要判断为"固定在平台大促/季末节点集中购买 / 有一定活动窗口倾向 / 无明显集中度，购买较分散"之一。
6. 折扣心智要区分 MD 占比和活动窗口集中度：MD 占比低但购买集中在大促/季末，不能写"折扣完全无感"；应写成"活动节点型决策/平台大促期购买习惯"。MD 占比高且集中在大促，才判断为强折扣心智、价格敏感。
7. 品类偏好要同时看细分品类和大类：Polo、T恤、针织、夹克/外套等都应归入男士上装/成衣偏好；鞋、包、皮具、皮带等作为扩展品类。不能把最高频品类写成全部订单。

⚠️ 输出风格约束（与 DeepSeek V4 Pro 统一标准）：

8. 简洁直接，不要啰嗦
   - summary 是给客服看的，直接写结论，不要解释分析过程
   - 2-3 句话讲清楚核心特征：客户类型、忠诚度、核心关注点、活跃度
   - summary 只保留结论，不输出证据清单，不要逐项罗列品类占比
   - 不要写"历史xx单，AOV xx，购买高峰明显集中在xx"等模板化开头
   - 不要把"安徽蚌埠""海口"等页面已展示的地址信息写进 summary

9. 拒绝废话和通用表述
   - ❌ 禁止："追求高品质生活""注重性价比""品质追求型""品味""生活方式""仪式感"
   - ❌ 禁止："具有明确消费目标""显示出对XX的向往""自我犒赏心理"
   - ❌ 禁止："根据XX""基于XX""结合XX"等分析过程用语
   - ❌ 禁止：在没有数据支撑的情况下使用形容词
   - ✅ 要求：使用具体数字和事实，引用客户原话或具体行为

10. 奢侈品场景专业判断
    - 复购周期 109 天是中频（不是低频！奢侈品客单价高）
    - 跨年度复购（2024-2025-2026）是高忠诚度表现
    - Total Look 客户（多品类购买）价值高于单品类的客户
    - 烟斗必须按价格带判断：4000-8000 普通斗，8000-12000 生肖斗，20000+ 高端限量斗

11. 活跃度评估原则
    - 活跃度只看最近购买或最近聊天，二者取其一即可，不要同时混写
    - 最近有购买但少聊天，不等于低活跃或流失
    - 不要写"0天活跃""0天未聊"这类绝对化表述

先逐项完成 trait_dimensions。每一项都不能留空：
- category_preference: 单品类专注/男士上装集中/多品类探索/跨品类扩展弱，并写证据。
- discount_mindset: MD 占比、FP/MD 结构、大促窗口集中度，判断折扣心智。
- price_sensitivity: 高/中/低/证据不足，说明依据。
- purchase_timing: 必须写购买时段集中度和大促/季末判断。
- chat_concerns: 聊天中的尺码、版型、材质、库存、物流、退换货、价格、搭配、礼品等关注点；无证据写"聊天证据不足"。
- communication_style: 决策方式和沟通风格，例如直接下单、反复确认、专业参数型、售后问题驱动、沉默型。
- pain_or_growth_opportunity: 后续运营需要解决和提升的点。

统一事实包：
{json.dumps(compact_context, ensure_ascii=False, indent=2, default=str)[:6000]}

只返回合法 JSON，不要 Markdown，不要解释推理过程。字段必须完整：
{{
  "trait_dimensions": {{
    "category_preference": "结合细分品类和大类的判断，带证据",
    "discount_mindset": "结合MD占比、FP/MD和大促窗口的判断，带证据",
    "price_sensitivity": "高/中/低/证据不足，带证据",
    "purchase_timing": "固定在平台大促/季末节点集中购买 / 有一定活动窗口倾向 / 无明显集中度，购买较分散，带证据",
    "chat_concerns": "聊天关注点/顾虑/退换货原因；无证据写聊天证据不足",
    "communication_style": "从聊天和下单节奏提炼决策风格",
    "pain_or_growth_opportunity": "需要解决或提升的关键点"
  }},
  "summary": "2-3句话，自然总结客户类型、忠诚度、核心关注点、活跃度。只保留结论，不输出证据清单，不要逐项罗列品类占比，不要模板化开头",
  "key_interests": ["2-4 个**短语标签**（2-6 字），如'高折扣心智'/'大促集中下单'/'Total Look多品类'/'高频复购'/'同日多件凑单'/'成衣主导'，每条就是一个词组，不写完整句子"],
  "pain_points": ["1-3 个**短语标签**（2-6 字），如'退款率偏高'/'VIP漏升风险'/'品类单一'/'缺聊天数据'，每条就是一个词组，不写完整句子"],
  "recommended_action": "1-2句话，说明触达时机、话术方向、推荐品类/商品方向",
  "confidence_level": "高/中/低"
}}

⚠️ 质量检查清单（每次分析前自检）：
1. [ ] 客户类型判断准确（Total Look / 品类专注 / 探索）？
2. [ ] summary 是否 2-3 句话、只保留结论？
3. [ ] 没有使用黑名单词汇（"品味""生活方式""根据XX"等）？
4. [ ] 没有模板化开头（"该客户为""历史XX单"等）？
5. [ ] 活跃度只用购买或聊天其一，没写"0天"？
6. [ ] recommended_action 具体到时机和方向？
7. [ ] 品类名保留英文原名，没翻译成中文？

违反任何一项，重新分析！
"""
