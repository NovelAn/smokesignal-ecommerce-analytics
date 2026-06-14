"""
DeepSeek AI Client - DeepSeek-R1推理模型集成
用于客户画像深度分析
"""
import json
import re
import sys
from datetime import datetime
from typing import Dict, List, Any
from openai import OpenAI
from backend.config import settings


def _safe_print(message: str):
    """Safe print that handles Windows GBK encoding issues"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback: encode to ASCII with replacement for unsupported chars
        print(message.encode('ascii', errors='replace').decode('ascii'))
from backend.ai.prompts.evidence_extraction import EVIDENCE_EXTRACTION_PROMPT
from backend.ai.prompts.persona_inference import PERSONA_INFERENCE_PROMPT
from backend.ai.prompts.domain_knowledge import build_external_info_context
from backend.ai.prompts.sentiment_intent_prompt import build_sentiment_intent_prompt
from backend.ai.data_extractor import extract_chat_insights
from backend.ai.behavior_analyzer import build_order_facts, structure_order_behavior
from backend.ai.persona_context import build_persona_prompt_v3


def _serialize_datetime(obj: Any) -> Any:
    """
    Convert datetime objects to ISO format strings for JSON serialization

    Args:
        obj: Any object (typically dict, list, or datetime)

    Returns:
        Object with datetimes converted to strings
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: _serialize_datetime(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_serialize_datetime(item) for item in obj]
    else:
        return obj


def _extract_category_distribution(order_behavior: Dict[str, Any]) -> Dict[str, Any]:
    purchase_features = order_behavior.get("购买特征", {})
    distribution = purchase_features.get("真实品类分布", {})
    return distribution if isinstance(distribution, dict) else {}


def _format_category_distribution_guard(category_distribution: Dict[str, Any]) -> str:
    categories = category_distribution.get("categories") or []
    if not categories:
        return "订单缺少可用category字段。禁止写“100%为某品类”或“只购买某品类”；只能说明“品类数据不足，无法判断占比”。"

    summary = category_distribution.get("summary", "")
    top_category = category_distribution.get("top_category", "未知")
    top_percentage = float(category_distribution.get("top_percentage") or 0)
    single_category = bool(category_distribution.get("single_category"))

    if single_category:
        return f"真实品类分布：{summary}。只有在此情况下才允许写“100%为{top_category}”。"

    return (
        f"真实品类分布：{summary}。最高品类是{top_category} {top_percentage:.1f}%。"
        "严禁写“100%为某品类”“历史订单均为某品类”“只购买某品类”。"
        "客户类型必须按该分布判断；若最高品类未达到80%，不要写品类专注型。"
    )


def _build_category_stage_note(category_distribution: Dict[str, Any]) -> str:
    stage_summary = category_distribution.get("stage_summary", "")
    if stage_summary:
        return f"品类阶段变化：{stage_summary}"
    return ""


def _parse_order_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:len(fmt)], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _build_purchase_timing_guard(
    profile: Dict[str, Any],
    orders: List[Dict[str, Any]],
    category_distribution: Dict[str, Any]
) -> str:
    dated_orders = []
    for order in orders:
        paid_at = _parse_order_datetime(
            order.get("pay_time") or order.get("最后付款时间") or order.get("payment_time")
        )
        if paid_at:
            dated_orders.append((paid_at, order))

    l6m_orders = int(_safe_float(profile.get("l6m_orders")))
    l6m_netsales = _safe_float(profile.get("l6m_netsales"))
    l6m_refund_rate = _safe_float(profile.get("l6m_refund_rate"))
    historical_refund = _safe_float(profile.get("historical_refund"))
    refund_rate = _safe_float(profile.get("refund_rate"))
    lines = [
        f"L6M订单数：{l6m_orders}；L6M净销售：¥{l6m_netsales:,.0f}；"
        f"L6M退款率：{l6m_refund_rate:.1%}；历史退款额：¥{historical_refund:,.0f}；"
        f"历史退款率/RRC：{refund_rate:.1%}。"
    ]

    if not dated_orders:
        return "\n".join(lines + ["订单缺少付款时间，禁止判断近期品类或召回间隔。"])

    dated_orders.sort(key=lambda item: item[0])
    latest_dt = dated_orders[-1][0]
    latest_day = latest_dt.date()
    latest_orders = [order for paid_at, order in dated_orders if paid_at.date() == latest_day]
    previous_dates = sorted({paid_at.date() for paid_at, _ in dated_orders if paid_at.date() < latest_day})
    latest_categories = sorted({
        str(order.get("category", "")).strip().upper()
        for order in latest_orders
        if str(order.get("category", "")).strip()
    })
    historical_categories = sorted({
        str(order.get("category", "")).strip().upper()
        for paid_at, order in dated_orders
        if paid_at.date() < latest_day and str(order.get("category", "")).strip()
    })
    non_recent_categories = [cat for cat in historical_categories if cat not in latest_categories]

    latest_payment = sum(_safe_float(order.get("payment") or order.get("成交总金额")) for order in latest_orders)
    latest_refund = sum(_safe_float(order.get("退款金额")) for order in latest_orders)
    latest_net = latest_payment - latest_refund
    latest_category_text = " / ".join(latest_categories) if latest_categories else "未知"
    lines.append(
        f"最近一次购买日期：{latest_day}；最近购买品类仅为：{latest_category_text}；"
        f"最近一次订单净销售约¥{latest_net:,.0f}。"
    )

    if previous_dates:
        previous_day = previous_dates[-1]
        gap_days = (latest_day - previous_day).days
        lines.append(f"上一购买日期：{previous_day}；与最近购买间隔约{gap_days}天。")
        if gap_days >= 365:
            lines.append("这是近期被召回的老客信号，summary必须体现“近期被召回/重新购买”，不要写成连续近期多品类购买。")
        elif gap_days >= 180:
            lines.append("这是较长间隔后的回购信号，summary应体现回购间隔，不要把历史品类说成近期购买。")

    if non_recent_categories:
        lines.append(
            f"非近期历史品类：{' / '.join(non_recent_categories)}。这些品类不是近期购买，禁止写“近期购买{('/'.join(non_recent_categories))}”。"
        )

    categories = category_distribution.get("categories") or []
    if categories:
        top_items = "、".join(
            f"{item.get('category')} {item.get('percentage')}%"
            for item in categories[:2]
        )
        lines.append(f"历史Top品类只代表全历史分布：{top_items}；不要等同于最近一次购买。")

    if l6m_orders > 0 and (l6m_netsales <= 0 or l6m_refund_rate >= 0.8):
        lines.append("近6个月有购买但净销售为0或退款率极高，这是关键风险；summary必须写“高退货/无净销售”，不能只写购买活跃。")
    elif historical_refund <= 0 and refund_rate <= 0 and l6m_refund_rate <= 0:
        lines.append("退款事实约束：RRC/历史退款率为0且L6M退款率为0，禁止写“高退货风险”“退货风险”“订单未完成风险”。尺码不合适、缺货、等待换货只能写为尺码/库存问题，不能升级为退货风险。")

    return "\n".join(lines)


def _compact_persona_summary(summary: str, max_chars: int = 170) -> str:
    if not isinstance(summary, str):
        return ""

    text = re.sub(r"\s+", " ", summary).strip()
    text = re.sub(r"^该客户为", "", text)
    text = re.sub(r"^客户为", "", text)
    text = re.sub(r"属于[^，。；]*客户", "客户", text)
    text = re.sub(r"(安徽|江苏|浙江|广东|福建|山东|河南|河北|湖南|湖北|四川|重庆|北京|上海|天津|海南|广西|云南|贵州|陕西|山西|江西|甘肃|青海|辽宁|吉林|黑龙江|内蒙古|新疆|西藏|宁夏|香港|澳门)[^，。；]*", "", text)
    text = re.sub(r"真实订单品类分布为[:：][^。]*[。]?", "", text)
    text = re.sub(r"真实订单品类分布[^。]*[。]?", "", text)
    text = re.sub(r"最高品类[^。]*[。]?", "", text)
    text = re.sub(r"品类阶段变化为[:：][^。]*", "", text)
    text = re.sub(r"品类阶段变化[:：][^。]*", "", text)
    text = re.sub(r"\d{4}\s*[:：][^；。]*(?:[；;]\s*)?", "", text)
    text = re.sub(r"；\s*。", "。", text)
    text = re.sub(r"。{2,}", "。", text).strip(" ，,；;。")

    if len(text) <= max_chars:
        return text

    sentences = [s.strip() for s in re.split(r"(?<=[。.!！?？])", text) if s.strip()]
    compact = ""
    for sentence in sentences:
        if len(compact + sentence) > max_chars:
            break
        compact += sentence
    if compact:
        return compact.strip(" ，,；;。")
    return text[:max_chars].rstrip("，。；,. ")


def _looks_template_like(summary: str) -> bool:
    if not isinstance(summary, str):
        return False
    markers = [
        "该客户为",
        "属于",
        "潜在高端",
        "模板",
        "客户画像",
        "高价值客户",
        "潜在客户"
    ]
    return any(marker in summary for marker in markers)


def _normalize_bullet_list(items: Any, max_items: int = 4, max_len: int = 40) -> List[str]:
    if not isinstance(items, list):
        return []
    normalized = []
    for item in items:
        if not isinstance(item, str):
            item = str(item)
        text = re.sub(r"\s+", " ", item).strip()
        if not text:
            continue
        if len(text) > max_len:
            text = text[:max_len].rstrip("，,。；; ")
        normalized.append(text)
        if len(normalized) >= max_items:
            break
    return normalized


def _apply_pipe_price_band_guard(summary: str, profile: Dict[str, Any], orders: List[Dict[str, Any]]) -> str:
    if not isinstance(summary, str):
        return summary

    top_category = str(profile.get("top_category", "")).upper()
    if top_category != "PIPES":
        return summary

    l6m_orders = int(_safe_float(profile.get("l6m_orders")))
    avg_order_value = 0.0
    latest_order_value = 0.0

    if orders:
        dated_orders = []
        for order in orders:
            paid_at = _parse_order_datetime(order.get("pay_time") or order.get("最后付款时间") or order.get("payment_time"))
            value = _safe_float(order.get("payment") or order.get("成交总金额"))
            if paid_at and value > 0:
                dated_orders.append((paid_at, value))
        if dated_orders:
            dated_orders.sort(key=lambda item: item[0])
            latest_order_value = dated_orders[-1][1]

    if l6m_orders > 0:
        avg_order_value = _safe_float(profile.get("l6m_netsales")) / max(l6m_orders, 1)
    if avg_order_value <= 0 and orders:
        order_values = []
        for order in orders:
            value = _safe_float(order.get("payment") or order.get("成交总金额"))
            if value > 0:
                order_values.append(value)
        if order_values:
            avg_order_value = sum(order_values) / len(order_values)

    order_value = latest_order_value or avg_order_value

    if order_value >= 20000:
        if "高端限量斗" not in summary and "限量斗" not in summary:
            summary = f"{summary.rstrip('。')}。若为限量编号或稀缺款，可按高端限量斗理解。"
        return summary

    if 12000 <= order_value < 20000:
        summary = re.sub(r"高端限量斗|高端收藏|收藏型客户|收藏", "生肖斗/限量编号款", summary)
        if "生肖斗" not in summary and "限量编号" not in summary:
            summary = f"{summary.rstrip('。')}。该单更接近生肖斗/限量编号款，不宜直接定义为高端收藏。"
        return summary

    if 8000 <= order_value < 12000:
        summary = re.sub(r"高端限量斗|高端收藏|收藏型客户|收藏", "生肖斗", summary)
        if "生肖斗" not in summary:
            summary = f"{summary.rstrip('。')}。该单属于生肖斗价位，不宜写成高端收藏。"
        return summary

    if order_value > 0:
        summary = re.sub(r"高端限量斗|高端收藏|收藏型客户|收藏|高端烟斗", "普通斗", summary)
        if "普通斗" not in summary:
            summary = f"{summary.rstrip('。')}。该单属于普通斗价位，不宜写成高端收藏。"
    return summary


def _sanitize_persona_category_claims(
    result: Dict[str, Any],
    category_distribution: Dict[str, Any],
    profile: Dict[str, Any] | None = None,
    orders: List[Dict[str, Any]] | None = None
) -> Dict[str, Any]:
    categories = category_distribution.get("categories") or []
    if not categories:
        summary_text = result.get("summary")
        if isinstance(summary_text, str):
            result["summary"] = _compact_persona_summary(
                _enforce_purchase_risk_summary(summary_text, profile or {}, orders or [])
            )
        return result

    single_category = bool(category_distribution.get("single_category"))
    top_category = category_distribution.get("top_category", "未知")
    top_percentage = float(category_distribution.get("top_percentage") or 0)

    invalid_patterns = [
        r"100%\s*为[^，。；,.]*",
        r"[^，。；,.]*品类\s*100%",
        r"[^，。；,.]*100%\s*品类",
        r"历史订单(?:均|全部|全都)[^，。；,.]*",
        r"(?:只|仅|完全|全部)购买[^，。；,.]*",
        r"均集中在[^，。；,.]*",
        r"专注[^，。；,.]*品类",
    ]

    summary_text = result.get("summary")
    if isinstance(summary_text, str):
        summary_text = re.sub(r"\s+", " ", summary_text).strip()
        if not single_category and any(re.search(pattern, summary_text) for pattern in invalid_patterns):
            summary_text = re.sub("|".join(invalid_patterns), "多品类购买", summary_text)
        if "品类专注型" in summary_text and top_percentage < 80:
            summary_text = summary_text.replace("品类专注型", "多品类客户")
        if "JEWELLERY" in summary_text and "JEWELLERY、" not in summary_text and top_percentage < 80:
            summary_text = summary_text.replace("JEWELLERY", "JEWELLERY（最高品类）")
        summary_text = _apply_pipe_price_band_guard(summary_text, profile or {}, orders or [])
        result["summary"] = _compact_persona_summary(
            _enforce_purchase_risk_summary(summary_text, profile or {}, orders or [])
        )

    interests = result.get("key_interests")
    if isinstance(interests, list):
        result["key_interests"] = [
            item for item in interests
            if not (isinstance(item, str) and ("品类阶段变化" in item or "真实订单品类分布" in item))
        ]

    customer_tags = result.get("customer_tags")
    if isinstance(customer_tags, dict):
        customer_type = str(customer_tags.get("客户类型", ""))
        if "品类专注" in customer_type and top_percentage < 80:
            customer_tags["客户类型"] = "多品类客户"

    return result


def _enforce_purchase_risk_summary(summary: str, profile: Dict[str, Any], orders: List[Dict[str, Any]]) -> str:
    if not isinstance(summary, str):
        summary = ""

    historical_refund = _safe_float(profile.get("historical_refund"))
    refund_rate = _safe_float(profile.get("refund_rate"))
    l6m_refund_rate = _safe_float(profile.get("l6m_refund_rate"))

    dated_orders = []
    for order in orders:
        paid_at = _parse_order_datetime(
            order.get("pay_time") or order.get("最后付款时间") or order.get("payment_time")
        )
        if paid_at:
            dated_orders.append((paid_at, order))

    additions = []
    if len({paid_at.date() for paid_at, _ in dated_orders}) >= 2:
        dated_orders.sort(key=lambda item: item[0])
        latest_day = dated_orders[-1][0].date()
        previous_day = sorted({paid_at.date() for paid_at, _ in dated_orders if paid_at.date() < latest_day})[-1]
        gap_days = (latest_day - previous_day).days
        if gap_days >= 365 and "召回" not in summary and "长间隔" not in summary:
            additions.append("近期被召回的老客")

    l6m_orders = int(_safe_float(profile.get("l6m_orders")))
    l6m_netsales = _safe_float(profile.get("l6m_netsales"))
    l6m_refund_rate = _safe_float(profile.get("l6m_refund_rate"))
    if l6m_orders > 0 and (l6m_netsales <= 0 or l6m_refund_rate >= 0.8):
        if "无净销售" not in summary and "净销售为0" not in summary:
            additions.append("近6个月高退货且无净销售")
    else:
        summary = re.sub(r"[，,]?\s*(高退货/无净销售|高退货且无净销售|无净销售|净销售为0)", "", summary)

    if historical_refund <= 0 and refund_rate <= 0 and l6m_refund_rate <= 0:
        summary = re.sub(r"[，,]?\s*(高退货风险|退货风险|订单未完成风险|未完成风险)", "", summary)
        summary = re.sub(r"[，,]?\s*(高退货/无净销售|高退货且无净销售)", "", summary)
    elif l6m_orders > 0 and l6m_netsales > 0:
        summary = re.sub(r"[，,]?\s*(高退货风险|高退货风险|高退货)", "", summary)
        summary = re.sub(r"[，,]?\s*退货风险", "", summary)

    if not additions:
        return summary

    suffix = "，".join(additions)
    if not summary:
        return suffix
    return f"{summary.rstrip('。')}。{suffix}。"


class DeepSeekClient:
    """
    DeepSeek AI客户端 - 用于客户画像深度分析
    API文档：https://platform.deepseek.com/api-docs/
    """

    def __init__(self):
        """初始化DeepSeek客户端"""
        if not settings.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY not configured in settings")

        # Create httpx client with custom transport to bypass system proxy
        # This fixes SSL issues on Windows when system proxy is configured
        import httpx
        from httpx._transports.default import HTTPTransport

        # Create transport without proxy
        transport = HTTPTransport(proxy=None)
        http_client = httpx.Client(transport=transport)

        self.client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url="https://api.deepseek.com",
            http_client=http_client
        )
        # DeepSeek-V3.2 统一模型，分场景使用 chat 和 reasoner
        self.base_model = getattr(settings, 'deepseek_model', 'DeepSeek-V4')
        self.model_reasoner = 'deepseek-v4-pro'  # 有聊天记录时使用（深度推理）
        self.model_chat = 'deepseek-v4-flash'  # 无聊天记录时使用（快速分析）

    def analyze_buyer_persona(
        self,
        buyer_nick: str,
        profile: Dict[str, Any],
        chats: List[Dict],
        orders: List[Dict],
        is_incremental: bool = False
    ) -> Dict[str, Any]:
        """
        两阶段分析：证据提取 → 画像推理

        Args:
            buyer_nick: 买家昵称
            profile: 客户档案数据
            chats: 聊天记录列表
            orders: 订单列表
            is_incremental: Round 4 增量模式, chats 仅含新增部分 + 少量上下文

        Returns:
            {
                "summary": str,
                "key_interests": List[str],
                "pain_points": List[str],
                "recommended_action": str,
                "confidence_level": str,
                "evidence": Dict  # 可选：包含提取的证据
            }
        """
        try:
            # 阶段1：证据提取
            evidence = self._extract_evidence(buyer_nick, profile, chats, orders, is_incremental=is_incremental)
            order_behavior = structure_order_behavior(profile, orders)
            order_behavior_serialized = _serialize_datetime(order_behavior)
            category_distribution = _extract_category_distribution(order_behavior_serialized)
            evidence["_category_distribution_guard"] = _format_category_distribution_guard(category_distribution)
            evidence["_authoritative_category_distribution"] = category_distribution

            # 阶段2：画像推理
            persona = self._infer_persona(evidence, is_incremental=is_incremental)
            persona = _sanitize_persona_category_claims(persona, category_distribution, profile, orders)

            # 合并结果
            persona["evidence"] = evidence

            return persona

        except Exception as e:
            _safe_print(f"[DeepSeek] 分析失败: {e}")
            raise  # 让orchestrator处理降级

    def _extract_evidence(
        self,
        buyer_nick: str,
        profile: Dict,
        chats: List[Dict],
        orders: List[Dict],
        is_incremental: bool = False
    ) -> Dict:
        """
        阶段1：提取关键证据

        Returns:
            证据字典
        """
        # 数据预处理
        chat_insights = extract_chat_insights(chats, buyer_nick)
        order_behavior = structure_order_behavior(profile, orders)

        # 格式化为prompt
        formatted_chats = self._format_chats_for_evidence(chat_insights)
        # Serialize datetime objects to strings before JSON encoding
        order_behavior_serialized = _serialize_datetime(order_behavior)
        formatted_behavior = json.dumps(order_behavior_serialized, ensure_ascii=False, indent=2)
        category_distribution_guard = _format_category_distribution_guard(
            _extract_category_distribution(order_behavior_serialized)
        )

        # 格式化场外信息
        external_records = profile.get("external_records", [])
        formatted_external = build_external_info_context(external_records) if external_records else "暂无场外信息记录"

        _scope = ("【增量分析】以下是自上次分析以来的新增聊天 + 少量历史上下文。请重点关注新增信息。\n\n" if is_incremental else "")
        prompt = _scope + EVIDENCE_EXTRACTION_PROMPT.format(
            formatted_chats=formatted_chats,
            structured_behavior=formatted_behavior,
            buyer_nick=buyer_nick,
            city=profile.get("city", "未知"),
            vip_level=profile.get("vip_level", "Non-VIP"),
            buyer_type=profile.get("buyer_type", "UNKNOWN"),
            first_purchase_date=profile.get("first_purchase_date", ""),
            last_purchase_date=profile.get("last_purchase_date", ""),
            days_since_last_purchase=profile.get("days_since_last_purchase", 0),
            days_since_last_chat=profile.get("days_since_last_chat", 0),
            avg_repurchase_interval_days=profile.get("avg_repurchase_interval_days", 0),
            external_info=formatted_external,
            category_distribution_guard=category_distribution_guard
        )

        response = self.client.chat.completions.create(
            model=self.model_reasoner,
            messages=[
                {
                    "role": "system",
                    "content": "你是一位严谨的数据分析师，只提取事实，不进行推断。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=settings.deepseek_temperature_evidence,  # 0.3
            max_tokens=3000  # Increased from 1500 to prevent truncation
        )

        evidence_text = response.choices[0].message.content
        _safe_print(f"[DeepSeek] 证据提取完成，token使用: {response.usage.total_tokens}")

        # 记录成本
        from backend.monitoring.cost_monitor import get_cost_monitor
        cost_monitor = get_cost_monitor()
        cost_monitor.log_api_call(
            model=self.model_reasoner,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            buyer_nick=buyer_nick,
            method="DeepSeek-R1-Evidence"
        )

        return self._parse_json_response(evidence_text)

    def _infer_persona(self, evidence: Dict, is_incremental: bool = False) -> Dict:
        """
        阶段2：基于证据推断画像

        Args:
            evidence: 阶段1提取的证据

        Returns:
            画像分析结果
        """
        # Serialize datetime objects before JSON encoding
        evidence_serialized = _serialize_datetime(evidence)
        prompt = _scope + PERSONA_INFERENCE_PROMPT.format(
            evidence_json=json.dumps(evidence_serialized, ensure_ascii=False, indent=2)
        )

        response = self.client.chat.completions.create(
            model=self.model_reasoner,
            messages=[
                {
                    "role": "system",
                    "content": "你是一位资深电商客户洞察专家，擅长从数据中洞察客户心理。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=settings.deepseek_temperature_inference,  # 0.7
            max_tokens=2000
        )

        persona_text = response.choices[0].message.content
        _safe_print(f"[DeepSeek] 画像推理完成，token使用: {response.usage.total_tokens}")

        # 记录成本
        from backend.monitoring.cost_monitor import get_cost_monitor
        cost_monitor = get_cost_monitor()
        cost_monitor.log_api_call(
            model=self.model_reasoner,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            buyer_nick=evidence.get("buyer_nick", "unknown"),
            method="DeepSeek-R1-Inference"
        )

        return self._parse_json_response(persona_text)

    def analyze_buyer_persona_chat(
        self,
        buyer_nick: str,
        profile: Dict[str, Any],
        chats: List[Dict],
        orders: List[Dict],
        is_incremental: bool = False
    ) -> Dict[str, Any]:
        """
        使用Chat模型快速分析（成本优化方案）

        不分两阶段，直接使用Chat模型一次性分析
        成本: ~¥3 (vs R1的~¥7)

        适用于: 中等复杂度（10-20条聊天记录）

        Args:
            is_incremental: Round 4 增量模式
        """
        # 数据预处理
        chat_insights = extract_chat_insights(chats, buyer_nick)
        order_behavior = structure_order_behavior(profile, orders)

        # Serialize datetime objects before JSON encoding
        order_behavior_serialized = _serialize_datetime(order_behavior)
        order_facts = build_order_facts(profile, orders, top_n=12)
        category_distribution = _extract_category_distribution(order_behavior_serialized)
        category_distribution_guard = _format_category_distribution_guard(category_distribution)
        purchase_timing_guard = _build_purchase_timing_guard(profile, orders, category_distribution)

        # 格式化场外信息
        external_records = profile.get("external_records", [])
        formatted_external = build_external_info_context(external_records) if external_records else "暂无场外信息记录"

        # 简化的prompt（一次性分析）
        prompt = f"""
你是一位电商客户分析专家。请基于以下数据，快速分析客户画像。

【客户信息】
昵称：{buyer_nick}
VIP等级：{profile.get("vip_level", "Non-VIP")}
地区：{profile.get("city", "未知")}
是否VIC：{profile.get("is_vic", False)}
是否Smoker：{profile.get("is_smoker", False)}
L6M消费：¥{profile.get("l6m_netsales", 0):,.2f}
总订单数：{profile.get("total_orders", 0)}

【聊天记录】（最近{len(chats)}条）
{self._format_chats_for_evidence(chat_insights)[:900]}

【订单行为】
{json.dumps(order_behavior_serialized, ensure_ascii=False, indent=2)[:1800]}

【订单核心事实包】
{json.dumps(order_facts, ensure_ascii=False, indent=2)[:1800]}

【品类事实约束】
{category_distribution_guard}

【近期/历史购买事实约束】
{purchase_timing_guard}

【场外信息】（线下消费和私域沟通，仅供参考）
{formatted_external[:500]}

【输出要求】
summary必须是结论摘要，不要罗列年度品类清单或完整证据。必须区分“历史Top品类”和“最近一次购买品类”；如果存在长间隔回购，要写“近期被召回的老客/长间隔后回购”。如果L6M净销售为0或退款率>=80%，必须写出“高退货/无净销售”这个风险。
如果历史退款额=0、RRC=0、L6M退款率=0，禁止写“高退货风险”“退货风险”“订单未完成风险”；尺码不合适、缺货、等待换货只能写成尺码/库存问题，不能升级为退货风险。
请返回JSON格式：
{{
  "summary": "2-3句话画像总结，包含客户特征和购买偏好",
  "key_interests": ["兴趣1", "兴趣2", "兴趣3"],
  "pain_points": ["痛点1", "痛点2"],
  "recommended_action": "具体建议，包含下次沟通时机和推荐产品",
  "confidence_level": "高/中/低"
}}
"""
        max_chars = 8000 if is_incremental else 15000
        prompt = build_persona_prompt_v3(buyer_nick, profile, chats, orders, is_incremental=is_incremental, max_context_chars=max_chars)

        try:
            response = self.client.chat.completions.create(
                model=self.model_chat,  # 使用Chat模型
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位资深电商客户洞察专家，擅长从有限的数据中快速识别客户特征和需求。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1800
            )

            result_text = response.choices[0].message.content
            _safe_print(f"[DeepSeek-Chat] 快速分析完成，token使用: {response.usage.total_tokens}")

            # 记录成本
            from backend.monitoring.cost_monitor import get_cost_monitor
            cost_monitor = get_cost_monitor()
            cost_monitor.log_api_call(
                model=self.model_chat,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                buyer_nick=buyer_nick,
                method="DeepSeek-Chat"
            )

            result = self._parse_json_response_v2(result_text)
            if isinstance(result.get("summary"), str):
                result["summary"] = _compact_persona_summary(result["summary"], max_chars=260)
            result["key_interests"] = _normalize_bullet_list(result.get("key_interests"), max_items=5, max_len=80)
            result["pain_points"] = _normalize_bullet_list(result.get("pain_points"), max_items=4, max_len=80)
            if isinstance(result.get("recommended_action"), str):
                result["recommended_action"] = _compact_persona_summary(result["recommended_action"], max_chars=180)
            return _sanitize_persona_category_claims(result, category_distribution, profile, orders)

        except Exception as e:
            _safe_print(f"[DeepSeek-Chat] 快速分析失败: {e}")
            raise

    # Alias for backward compatibility
    analyze_buyer_persona_quick = analyze_buyer_persona_chat

    def _format_chats_for_evidence(self, chat_insights: Dict) -> str:
        """格式化聊天记录为证据提取prompt"""
        lines = []

        for i, chat in enumerate(chat_insights.get("完整对话", [])[:30], 1):
            sender = chat["发送者"]
            time = chat["时间"]
            content = chat["内容"]
            lines.append(f"[{i}] [{time}] {sender}: {content}")

        return "\n".join(lines)

    def _parse_json_response_v2(self, response_text: str) -> Dict:
        """Parse model JSON even when it includes thinking text or fences."""
        try:
            cleaned = re.sub(r"<think>.*?</think>", "", response_text or "", flags=re.DOTALL | re.IGNORECASE).strip()
            fence_match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL | re.IGNORECASE)
            if fence_match:
                cleaned = fence_match.group(1).strip()

            decoder = json.JSONDecoder()
            for match in re.finditer(r"\{", cleaned):
                try:
                    value, _ = decoder.raw_decode(cleaned[match.start():])
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    return value

            raise ValueError("no valid JSON object found")
        except Exception as e:
            _safe_print(f"[DeepSeek] JSON parse failed: {e}")
            _safe_print(f"[DeepSeek] Raw response: {(response_text or '')[:500]}")
            return {
                "summary": "AI分析结果解析失败",
                "key_interests": [],
                "pain_points": [],
                "recommended_action": "请根据客户情况制定跟进策略",
                "confidence_level": "低",
                "error": str(e)
            }

    def _parse_json_response(self, response_text: str) -> Dict:
        """解析JSON响应"""
        try:
            # 尝试提取JSON
            start = response_text.find('{')
            end = response_text.rfind('}') + 1

            if start != -1 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
            else:
                raise ValueError("未找到有效JSON")

        except Exception as e:
            _safe_print(f"[DeepSeek] JSON解析失败: {e}")
            _safe_print(f"[DeepSeek] 原始响应: {response_text[:500]}")

            # 返回默认结构
            return {
                "summary": "AI分析结果解析失败",
                "key_interests": [],
                "pain_points": [],
                "recommended_action": "请根据客户情况制定跟进策略",
                "confidence_level": "低",
                "error": str(e)
            }

    def analyze_sentiment_intent(
        self,
        buyer_nick: str,
        messages: List[str],
        is_incremental: bool = False
    ) -> Dict[str, Any]:
        """
        分析客户消息的情感和意图

        Args:
            buyer_nick: 买家昵称
            messages: 客户消息列表
            is_incremental: True=增量模式（messages 是自上次分析以来的新聊天）；
                          False=全量模式（messages 是买家全部历史聊天）。

        Returns:
            {
                "sentiment_score": float (0-1),
                "sentiment_label": str (Positive/Neutral/Negative),
                "intent_distribution": dict,
                "dominant_intent": str,
                "complaint_count": int
            }
        """
        if not messages:
            return {
                "sentiment_score": 0.5,
                "sentiment_label": "Neutral",
                "intent_distribution": {
                    "Pre-sale Inquiry": 0,
                    "Post-sale Support": 0,
                    "Logistics": 0,
                    "Usage Guide": 0,
                    "Complaint": 0,
                    "Inventory Inquiry": 0
                },
                "dominant_intent": "Unknown",
                "complaint_count": 0
            }

        prompt = build_sentiment_intent_prompt(messages, is_incremental=is_incremental)

        try:
            response = self.client.chat.completions.create(
                model=self.model_chat,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位专业的客户情感分析师，擅长从客户消息中分析情感倾向和意图。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )

            result_text = response.choices[0].message.content
            _safe_print(f"[DeepSeek] 情感分析完成，token使用: {response.usage.total_tokens}")

            # 记录成本
            from backend.monitoring.cost_monitor import get_cost_monitor
            cost_monitor = get_cost_monitor()
            cost_monitor.log_api_call(
                model=self.model_chat,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                buyer_nick=buyer_nick,
                method="DeepSeek-Sentiment"
            )

            result = self._parse_sentiment_response(result_text)
            result["sentiment_method"] = "deepseek"
            return result

        except Exception as e:
            _safe_print(f"[DeepSeek] 情感分析失败: {e}")
            raise

    def _parse_sentiment_response(self, response_text: str) -> Dict:
        """解析情感分析响应"""
        try:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1

            if start != -1 and end > start:
                json_str = response_text[start:end]
                result = json.loads(json_str)

                # 确保所有必要字段存在
                return {
                    "sentiment_score": float(result.get("sentiment_score", 0.5)),
                    "sentiment_label": result.get("sentiment_label", "Neutral"),
                    "intent_distribution": result.get("intent_distribution", {
                        "Pre-sale Inquiry": 0,
                        "Post-sale Support": 0,
                        "Logistics": 0,
                        "Usage Guide": 0,
                        "Complaint": 0,
                        "Inventory Inquiry": 0
                    }),
                    "dominant_intent": result.get("dominant_intent", "Unknown"),
                    "complaint_count": int(result.get("complaint_count", 0))
                }
            else:
                raise ValueError("未找到有效JSON")

        except Exception as e:
            _safe_print(f"[DeepSeek] 情感JSON解析失败: {e}")
            return {
                "sentiment_score": 0.5,
                "sentiment_label": "Neutral",
                "intent_distribution": {
                    "Pre-sale Inquiry": 0,
                    "Post-sale Support": 0,
                    "Logistics": 0,
                    "Usage Guide": 0,
                    "Complaint": 0,
                    "Inventory Inquiry": 0
                },
                "dominant_intent": "Unknown",
                "complaint_count": 0
            }
