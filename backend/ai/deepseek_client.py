"""
DeepSeek AI Client - DeepSeek-R1推理模型集成
用于客户画像深度分析
"""
import json
from datetime import datetime
from typing import Dict, List, Any
from openai import OpenAI
from backend.config import settings
from backend.ai.prompts.evidence_extraction import EVIDENCE_EXTRACTION_PROMPT
from backend.ai.prompts.persona_inference import PERSONA_INFERENCE_PROMPT
from backend.ai.prompts.domain_knowledge import build_external_info_context
from backend.ai.data_extractor import extract_chat_insights
from backend.ai.behavior_analyzer import structure_order_behavior


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
        self.base_model = getattr(settings, 'deepseek_model', 'DeepSeek-V3.2')
        self.model_reasoner = 'deepseek-reasoner'  # 有聊天记录时使用（深度推理）
        self.model_chat = 'deepseek-chat'  # 无聊天记录时使用（快速分析）

    def analyze_buyer_persona(
        self,
        buyer_nick: str,
        profile: Dict[str, Any],
        chats: List[Dict],
        orders: List[Dict]
    ) -> Dict[str, Any]:
        """
        两阶段分析：证据提取 → 画像推理

        Args:
            buyer_nick: 买家昵称
            profile: 客户档案数据
            chats: 聊天记录列表
            orders: 订单列表

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
            evidence = self._extract_evidence(buyer_nick, profile, chats, orders)

            # 阶段2：画像推理
            persona = self._infer_persona(evidence)

            # 合并结果
            persona["evidence"] = evidence

            return persona

        except Exception as e:
            print(f"[DeepSeek] 分析失败: {e}")
            raise  # 让orchestrator处理降级

    def _extract_evidence(
        self,
        buyer_nick: str,
        profile: Dict,
        chats: List[Dict],
        orders: List[Dict]
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

        # 格式化场外信息
        external_records = profile.get("external_records", [])
        formatted_external = build_external_info_context(external_records) if external_records else "暂无场外信息记录"

        prompt = EVIDENCE_EXTRACTION_PROMPT.format(
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
            external_info=formatted_external
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
        print(f"[DeepSeek] 证据提取完成，token使用: {response.usage.total_tokens}")

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

    def _infer_persona(self, evidence: Dict) -> Dict:
        """
        阶段2：基于证据推断画像

        Args:
            evidence: 阶段1提取的证据

        Returns:
            画像分析结果
        """
        # Serialize datetime objects before JSON encoding
        evidence_serialized = _serialize_datetime(evidence)
        prompt = PERSONA_INFERENCE_PROMPT.format(
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
        print(f"[DeepSeek] 画像推理完成，token使用: {response.usage.total_tokens}")

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
        orders: List[Dict]
    ) -> Dict[str, Any]:
        """
        使用Chat模型快速分析（成本优化方案）

        不分两阶段，直接使用Chat模型一次性分析
        成本: ~¥3 (vs R1的~¥7)

        适用于: 中等复杂度（10-20条聊天记录）
        """
        # 数据预处理
        chat_insights = extract_chat_insights(chats, buyer_nick)
        order_behavior = structure_order_behavior(profile, orders)

        # Serialize datetime objects before JSON encoding
        order_behavior_serialized = _serialize_datetime(order_behavior)

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
{self._format_chats_for_evidence(chat_insights)[:1500]}

【订单行为】
{json.dumps(order_behavior_serialized, ensure_ascii=False, indent=2)[:800]}

【场外信息】（线下消费和私域沟通，仅供参考）
{formatted_external[:500]}

【输出要求】
请返回JSON格式：
{{
  "summary": "2-3句话画像总结，包含客户特征和购买偏好",
  "key_interests": ["兴趣1", "兴趣2", "兴趣3"],
  "pain_points": ["痛点1", "痛点2"],
  "recommended_action": "具体建议，包含下次沟通时机和推荐产品",
  "confidence_level": "高/中/低"
}}
"""

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
                temperature=0.5,
                max_tokens=1500
            )

            result_text = response.choices[0].message.content
            print(f"[DeepSeek-Chat] 快速分析完成，token使用: {response.usage.total_tokens}")

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

            return self._parse_json_response(result_text)

        except Exception as e:
            print(f"[DeepSeek-Chat] 快速分析失败: {e}")
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
            print(f"[DeepSeek] JSON解析失败: {e}")
            print(f"[DeepSeek] 原始响应: {response_text[:500]}")

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
        messages: List[str]
    ) -> Dict[str, Any]:
        """
        分析客户消息的情感和意图

        Args:
            buyer_nick: 买家昵称
            messages: 客户消息列表

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
                    "Complaint": 0
                },
                "dominant_intent": "Unknown",
                "complaint_count": 0
            }

        prompt = f"""分析以下客户消息的情感和意图。

客户消息（最近{len(messages)}条）:
{chr(10).join([f'- {msg}' for msg in messages[:20]])}

请分析并返回JSON格式结果：
{{
    "sentiment_score": 情感分数(0-1, 0=非常消极, 1=非常积极),
    "sentiment_label": "Positive"或"Neutral"或"Negative",
    "intent_distribution": {{
        "Pre-sale Inquiry": 售前咨询相关消息数量,
        "Post-sale Support": 售后支持相关消息数量,
        "Logistics": 物流相关消息数量,
        "Usage Guide": 使用指南相关消息数量,
        "Complaint": 投诉相关消息数量
    }},
    "dominant_intent": "主要意图(上述数量最多的类别)",
    "complaint_count": 投诉相关消息总数
}}

【重要】情感分数(sentiment_score)判断标准：

一、Neutral（0.4-0.6）：正常的业务咨询
- 询问库存、价格、物流："有没有货""什么时候发货""多少钱"
- 表达疑惑或好奇："怎么下架了""就一个吗""为什么"
- 功能性请求："退款""退货""换货"
- 带语气词的询问："到底有没有啊""怎么这样"（语气词≠负面情绪）

二、Negative（< 0.4）：只有明确负面表达时才判为负面
- 包含投诉词汇："我要投诉""给差评""举报"
- 包含负面评价词："太差""垃圾""骗子""假货""失望""不满"
- 表达愤怒或强烈不满

三、Positive（> 0.6）：明确的正面情绪
- 表达感谢、满意、赞赏
- 再次购买意愿、推荐他人

【重要】Complaint判断标准（非常严格）：

只有满足以下条件才算投诉：
1. 明确的投诉行为词汇：投诉/差评/举报/315/消费者协会/工商/找经理
2. 明确的负面评价词：太差/质量差/很差/垃圾/骗子/假货/欺骗/失望/不满/态度差/服务差/恶心/坑人

【示例】：
- "质量太差了" → Negative(0.2), Complaint
- "我要投诉你们" → Negative(0.2), Complaint
- "有没有货啊到底" → Neutral(0.5), Logistics（询问≠负面）
- "怎么买完就下架啊" → Neutral(0.5), Post-sale Support（疑惑≠负面）
- "就一个啊？" → Neutral(0.5), Pre-sale Inquiry

只返回JSON，不要其他内容。"""

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
            print(f"[DeepSeek] 情感分析完成，token使用: {response.usage.total_tokens}")

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
            print(f"[DeepSeek] 情感分析失败: {e}")
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
                        "Complaint": 0
                    }),
                    "dominant_intent": result.get("dominant_intent", "Unknown"),
                    "complaint_count": int(result.get("complaint_count", 0))
                }
            else:
                raise ValueError("未找到有效JSON")

        except Exception as e:
            print(f"[DeepSeek] 情感JSON解析失败: {e}")
            return {
                "sentiment_score": 0.5,
                "sentiment_label": "Neutral",
                "intent_distribution": {
                    "Pre-sale Inquiry": 0,
                    "Post-sale Support": 0,
                    "Logistics": 0,
                    "Usage Guide": 0,
                    "Complaint": 0
                },
                "dominant_intent": "Unknown",
                "complaint_count": 0
            }
