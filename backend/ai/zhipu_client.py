"""
Zhipu AI (GLM-4.7) client for buyer persona analysis
"""
import json
from typing import Dict, List, Any
from zhipuai import ZhipuAI
from backend.config import settings


class ZhipuClient:
    """Zhipu AI client for intelligent buyer analysis"""

    def __init__(self):
        self.client = ZhipuAI(api_key=settings.zhipu_api_key)
        self.model = settings.zhipu_model

    def analyze_buyer_persona(
        self,
        user_nick: str,
        profile_data: Dict[str, Any],
        recent_chats: List[Dict[str, Any]],
        order_summary: str
    ) -> Dict[str, Any]:
        """
        Analyze buyer persona using Zhipu AI

        Args:
            user_nick: Buyer nickname
            profile_data: Buyer profile metrics
            recent_chats: Recent chat messages (last 20)
            order_summary: Summary of order history

        Returns:
            {
                "summary": str,
                "key_interests": List[str],
                "pain_points": List[str],
                "recommended_action": str
            }
        """
        prompt = self._build_persona_prompt(user_nick, profile_data, recent_chats, order_summary)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位资深的电商客户分析专家，擅长从订单数据和聊天记录中分析买家的购买行为、偏好和需求。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1500
            )

            response_text = response.choices[0].message.content
            return self._parse_ai_response(response_text)

        except Exception as e:
            print(f"Error calling Zhipu AI: {e}")
            return self._default_analysis()

    def _build_persona_prompt(
        self,
        user_nick: str,
        profile: Dict[str, Any],
        chats: List[Dict],
        order_summary: str
    ) -> str:
        """Build prompt for buyer persona analysis"""
        # 构建深度分析指令
        prompt = f"""
你是一位资深电商客户洞察专家。请基于以下数据进行深度买家画像分析，**不要简单重复数据**，而是要挖掘背后的行为模式、心理动机和潜在需求。

【买家数据】
{order_summary}

【聊天记录】（最近{len(chats)}条）
{self._format_chats(chats[:20])}

**分析要求：**

1. **summary** - 深度画像总结（2-3句话）
   - ❌ 不要说："来自XX的客户，消费了XX元"
   - ✅ 要分析：购买决策模式、价值取向、消费心理特征
   - 例如："这是一位注重品质胜过价格的务实型买家，首次购买即选择高价位PIPES产品，显示出明确的目标性和较强的支付意愿。"

2. **key_interests** - 隐性兴趣点（3-5个）
   - ❌ 不要："来自北京"、"喜欢PIPES"
   - ✅ 要推断：生活方式、价值观、潜在需求
   - 例如：["专业烟斗玩家追求品质体验", "重视产品专业性和设计感", "愿意为品质支付溢价"]

3. **pain_points** - 潜在痛点（2-4个）
   - 基于消费行为和聊天内容推断未被满足的需求或担忧
   - 例如：["可能需要专业的产品使用指导", "对产品真伪和品质有疑虑", "缺乏同类产品对比信息"]

4. **recommended_action** - 个性化跟进策略（1-2句话）
   - 具体的、可执行的、针对该买家的独特建议
   - 例如："主动提供PIPES产品的专业使用指南和保养建议，建立专业顾问形象，增强信任感"

**输出格式（纯JSON，不要其他文字）：**
{{
  "summary": "深度画像总结...",
  "key_interests": ["推断的兴趣点1", "兴趣点2", "兴趣点3"],
  "pain_points": ["推断的痛点1", "痛点2"],
  "recommended_action": "个性化建议..."
}}
"""
        return prompt

    def _format_chats(self, chats: List[Dict]) -> str:
        """Format chat messages for prompt"""
        if not chats:
            return "暂无聊天记录"

        formatted = []
        for chat in reversed(chats):  # Show in chronological order
            sender = chat.get('sender_nick', 'Unknown')
            content = chat.get('content', '')[:100]  # Limit length
            time = chat.get('msg_time', '')
            formatted.append(f"[{time}] {sender}: {content}")

        return "\n".join(formatted)

    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response and extract JSON"""
        try:
            # Try to extract JSON from response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1

            if start != -1 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
            else:
                # If no JSON found, return as summary
                return {
                    "summary": response_text[:500],
                    "key_interests": [],
                    "pain_points": [],
                    "recommended_action": "请根据买家情况制定跟进策略"
                }

        except json.JSONDecodeError as e:
            print(f"Error parsing AI response: {e}")
            return {
                "summary": response_text[:500] if response_text else "AI分析失败",
                "key_interests": [],
                "pain_points": [],
                "recommended_action": "请根据买家情况制定跟进策略"
            }

    def _default_analysis(self) -> Dict[str, Any]:
        """Return default analysis when AI fails"""
        return {
            "summary": "暂无AI分析",
            "key_interests": [],
            "pain_points": [],
            "recommended_action": "建议根据买家历史购买情况制定个性化跟进方案"
        }

    def analyze_sentiment_batch(self, messages: List[str]) -> List[Dict[str, Any]]:
        """
        Batch analyze sentiment for messages

        Returns sentiment score (0-1) and category for each message
        """
        if not messages:
            return []

        prompt = f"""
请分析以下买家消息的情绪倾向，对每条消息给出：
- 情绪分数（0-1，0表示非常负面，0.5中性，1非常正面）
- 情绪分类（Positive/Neutral/Negative）

消息列表：
{self._format_messages_for_sentiment(messages)}

请以JSON数组格式返回：
[
  {{"score": 0.8, "sentiment": "Positive"}},
  {{"score": 0.3, "sentiment": "Negative"}},
  ...
]
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个情绪分析专家，擅长识别文本中的情绪倾向。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=2000
            )

            response_text = response.choices[0].message.content
            return self._parse_sentiment_response(response_text, len(messages))

        except Exception as e:
            print(f"Error in sentiment analysis: {e}")
            return [{"score": 0.5, "sentiment": "Neutral"}] * len(messages)

    def _format_messages_for_sentiment(self, messages: List[str]) -> str:
        """Format messages for sentiment analysis"""
        formatted = []
        for i, msg in enumerate(messages):
            formatted.append(f"{i+1}. {msg[:200]}")
        return "\n".join(formatted)

    def _parse_sentiment_response(self, response_text: str, expected_count: int) -> List[Dict[str, Any]]:
        """Parse sentiment analysis response"""
        try:
            start = response_text.find('[')
            end = response_text.rfind(']') + 1

            if start != -1 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
            else:
                # Return neutral for all
                return [{"score": 0.5, "sentiment": "Neutral"}] * expected_count

        except json.JSONDecodeError:
            return [{"score": 0.5, "sentiment": "Neutral"}] * expected_count

    def extract_intent_distribution(self, messages: List[str]) -> Dict[str, int]:
        """
        Analyze intent distribution from messages

        Returns counts for: Pre-sale, Post-sale, Logistics, Usage Guide, Complaint
        """
        prompt = f"""
请分析以下买家消息的意图类型，将每条消息分类到以下类型之一：
1. Pre-sale Inquiry (售前咨询) - 询问产品、价格、推荐等
2. Post-sale Support (售后支持) - 收到产品后的问题反馈
3. Logistics (物流) - 关于发货、快递、物流跟踪
4. Usage Guide (使用指南) - 询问如何使用、保养等
5. Complaint (投诉) - 明确的投诉、不满

消息列表：
{self._format_messages_for_sentiment(messages)}

请返回每种类型的数量（JSON格式）：
{{
  "Pre-sale Inquiry": 数量,
  "Post-sale Support": 数量,
  "Logistics": 数量,
  "Usage Guide": 数量,
  "Complaint": 数量
}}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个客户服务意图分析专家。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=500
            )

            response_text = response.choices[0].message.content
            return self._parse_intent_response(response_text)

        except Exception as e:
            print(f"Error in intent analysis: {e}")
            return {
                "Pre-sale Inquiry": 0,
                "Post-sale Support": 0,
                "Logistics": 0,
                "Usage Guide": 0,
                "Complaint": 0
            }

    def _parse_intent_response(self, response_text: str) -> Dict[str, int]:
        """Parse intent analysis response"""
        try:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1

            if start != -1 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
            else:
                return self._default_intent_distribution()

        except json.JSONDecodeError:
            return self._default_intent_distribution()

    def _default_intent_distribution(self) -> Dict[str, int]:
        """Return default intent distribution"""
        return {
            "Pre-sale Inquiry": 0,
            "Post-sale Support": 0,
            "Logistics": 0,
            "Usage Guide": 0,
            "Complaint": 0
        }
