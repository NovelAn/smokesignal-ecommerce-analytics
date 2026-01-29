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

        self.client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url="https://api.deepseek.com"
        )
        self.model_r1 = settings.deepseek_model_r1  # "deepseek-reasoner"
        self.model_chat = settings.deepseek_model_chat  # "deepseek-chat"

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
        chat_insights = extract_chat_insights(chats)
        order_behavior = structure_order_behavior(profile, orders)

        # 格式化为prompt
        formatted_chats = self._format_chats_for_evidence(chat_insights)
        # Serialize datetime objects to strings before JSON encoding
        order_behavior_serialized = _serialize_datetime(order_behavior)
        formatted_behavior = json.dumps(order_behavior_serialized, ensure_ascii=False, indent=2)

        prompt = EVIDENCE_EXTRACTION_PROMPT.format(
            formatted_chats=formatted_chats,
            structured_behavior=formatted_behavior,
            buyer_nick=buyer_nick,
            city=profile.get("city", "未知"),
            vip_level=profile.get("vip_level", "Non-VIP"),
            buyer_type=profile.get("buyer_type", "UNKNOWN"),
            first_purchase_date=profile.get("first_purchase_date", ""),
            last_purchase_date=profile.get("last_purchase_date", "")
        )

        response = self.client.chat.completions.create(
            model=self.model_r1,
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
            model=self.model_r1,
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

        return self._parse_json_response(persona_text)

    def analyze_buyer_persona_quick(
        self,
        buyer_nick: str,
        profile: Dict[str, Any],
        chats: List[Dict],
        orders: List[Dict]
    ) -> Dict[str, Any]:
        """
        使用Chat模型快速分析（降级方案）

        不分两阶段，直接使用Chat模型一次性分析
        """
        # 数据预处理
        chat_insights = extract_chat_insights(chats)
        order_behavior = structure_order_behavior(profile, orders)

        # Serialize datetime objects before JSON encoding
        order_behavior_serialized = _serialize_datetime(order_behavior)

        # 简化的prompt（一次性分析）
        prompt = f"""
你是一位电商客户分析专家。请基于以下数据，快速分析客户画像。

【客户信息】
昵称：{buyer_nick}
VIP等级：{profile.get("vip_level", "Non-VIP")}
地区：{profile.get("city", "未知")}

【聊天记录】（最近{len(chats)}条）
{self._format_chats_for_evidence(chat_insights)[:1000]}

【订单行为】
{json.dumps(order_behavior_serialized, ensure_ascii=False, indent=2)[:500]}

【输出要求】
请返回JSON格式：
{{
  "summary": "2-3句话画像总结",
  "key_interests": ["兴趣1", "兴趣2", "兴趣3"],
  "pain_points": ["痛点1", "痛点2"],
  "recommended_action": "具体建议",
  "confidence_level": "高/中/低"
}}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model_chat,  # 使用Chat模型
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位电商客户分析专家。"
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

            return self._parse_json_response(result_text)

        except Exception as e:
            print(f"[DeepSeek-Chat] 快速分析失败: {e}")
            raise

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
