"""
MiniMax AI Client - 备选模型 (Fallback Model)
当DeepSeek API余额不足(429)或超时时，自动降级到此模型
当前使用: MiniMax-M2.7 (OpenAI兼容接口)
"""
import json
import re
from typing import Dict, List, Any
from openai import OpenAI
from backend.config import settings


def _safe_print(message: str):
    """Safe print that handles Windows GBK encoding issues"""
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        print(message.encode('ascii', errors='replace').decode('ascii'), flush=True)


class MiniMaxClient:
    """MiniMax AI client for buyer analysis (OpenAI-compatible API)"""

    def __init__(self):
        import httpx
        from httpx._transports.default import HTTPTransport

        transport = HTTPTransport(proxy=None)
        http_client = httpx.Client(transport=transport)

        self.client = OpenAI(
            api_key=settings.minimax_api_key,
            base_url=settings.minimax_base_url,
            http_client=http_client
        )
        self.model = settings.minimax_model

    def analyze_buyer_persona(
        self,
        user_nick: str,
        profile_data: Dict[str, Any],
        recent_chats: List[Dict[str, Any]],
        order_summary: str
    ) -> Dict[str, Any]:
        prompt = self._build_persona_prompt(user_nick, profile_data, recent_chats, order_summary)

        try:
            _safe_print(f"[MiniMaxClient] Calling model: {self.model}")

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
                temperature=0.3
            )

            response_text = response.choices[0].message.content
            _safe_print(f"[MiniMaxClient] Response length: {len(response_text) if response_text else 0}")
            _safe_print(f"[MiniMaxClient] Response preview: {response_text[:300] if response_text else 'EMPTY'}")

            return self._parse_ai_response(response_text)

        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate" in error_str or "insufficient" in error_str or "余额" in error_str:
                _safe_print(f"[MiniMaxClient] API余额不足(429): {e}")
            else:
                _safe_print(f"[MiniMaxClient] Error calling MiniMax AI: {e}")
            import traceback
            traceback.print_exc()
            return self._default_analysis()

    def _build_persona_prompt(
        self,
        user_nick: str,
        profile: Dict[str, Any],
        chats: List[Dict],
        order_summary: str
    ) -> str:
        prompt = f"""
你是一位资深电商客户洞察专家，专门基于消费数据进行深度分析，目标是创造销售机会、提高转化率、促活高价值客户。

⚠️ **核心要求**：
1. 使用具体数字和事实，不要用形容词
2. 禁止："追求品质"、"注重性价比"、"品质追求型"、"显示向往"
3. 简洁直接，2-3句话讲清楚
4. **深度分析**：从消费数据推断品类偏好、复购动机、促活机会

【买家数据】
{order_summary}

【聊天记录】（最近{len(chats)}条）
{self._format_chats(chats[:20])}

**分析要求：**

1. **summary** - 画像总结（2-3句话）
   - 使用具体数字：客单价、退款率、复购间隔、品类占比、MD占比等
   - **深度推断**：
     * 品类偏好：所有订单都是同一品类？→ 专注型客户，偏好明确
     * 复购行为：第二单隔多久？仍买同品类？→ 偏好稳定，可推荐同品类新品
     * 客单价变化：持续上升？→ 消费升级，可推荐更高价位商品
   - 如果有聊天，引用客户原话
   - ❌ 禁止："追求高品质生活"、"品质追求型"、"具有明确目标"

2. **key_interests** - 兴趣点（3-5个）
   - 基于真实数据推断偏好
   - ❌ 禁止："追求品质体验"、"重视专业性"
   - ✅ 示例：["JEWELLERY品类占90%", "平均客单价¥18,000", "聊天中询问'新品上市时间'", "偏好购买MD商品"]

3. **pain_points** - 痛点（2-4个）
   - 基于数据或聊天内容
   - ❌ 禁止："对品质有疑虑"、"需要专业指导"
   - ✅ 示例：["退款率12%（高于平均）", "聊天中提到'不知道怎么选'", "比价行为：3次询问价格"]

4. **recommended_action** - 跟进建议（1-2句话）
   - **具体的销售机会和执行建议**

**输出格式（纯JSON）：**
{{
  "summary": "具体数据支撑的总结，推断品类偏好、复购动机...",
  "key_interests": ["具体兴趣点1", "兴趣点2"],
  "pain_points": ["具体痛点1", "痛点2"],
  "recommended_action": "具体的销售机会和执行建议..."
}}
"""
        return prompt

    def _format_chats(self, chats: List[Dict]) -> str:
        if not chats:
            return "暂无聊天记录"

        formatted = []
        for chat in reversed(chats):
            sender = chat.get('sender_nick', 'Unknown')
            content = chat.get('content', '')[:100]
            time = chat.get('msg_time', '')
            formatted.append(f"[{time}] {sender}: {content}")

        return "\n".join(formatted)

    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        try:
            if not response_text:
                _safe_print("[MiniMaxClient] Response is empty!")
                return self._default_analysis()

            cleaned = self._clean_model_response(response_text)

            _safe_print(f"[MiniMaxClient] Cleaned response: {cleaned[:300]}")

            json_str = self._extract_json_value(cleaned, expected_type=dict)

            if json_str:
                result = json.loads(json_str)
                _safe_print("[MiniMaxClient] Parsed JSON successfully")
                return result
            else:
                _safe_print("[MiniMaxClient] No JSON found in response")
                return {
                    "summary": cleaned[:500],
                    "key_interests": [],
                    "pain_points": [],
                    "recommended_action": "请根据买家情况制定跟进策略"
                }

        except json.JSONDecodeError as e:
            _safe_print(f"[MiniMaxClient] JSON decode error: {e}")
            return {
                "summary": response_text[:500] if response_text else "AI分析失败",
                "key_interests": [],
                "pain_points": [],
                "recommended_action": "请根据买家情况制定跟进策略"
            }

    def _default_analysis(self) -> Dict[str, Any]:
        return {
            "summary": "暂无AI分析",
            "key_interests": [],
            "pain_points": [],
            "recommended_action": "建议根据买家历史购买情况制定个性化跟进方案"
        }

    def analyze_sentiment_batch(self, messages: List[str]) -> List[Dict[str, Any]]:
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

只返回合法JSON数组，不要输出解释、Markdown代码块或思考过程。
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
            _safe_print(f"[MiniMaxClient] Error in sentiment analysis: {e}")
            return self._default_sentiment_results(len(messages), parse_failed=True)

    def _format_messages_for_sentiment(self, messages: List[str]) -> str:
        formatted = []
        for i, msg in enumerate(messages):
            formatted.append(f"{i+1}. {msg[:200]}")
        return "\n".join(formatted)

    def _parse_sentiment_response(self, response_text: str, expected_count: int) -> List[Dict[str, Any]]:
        try:
            cleaned = self._clean_model_response(response_text)
            json_str = self._extract_json_value(cleaned, expected_type=list)

            if not json_str:
                _safe_print(f"[MiniMaxClient] No sentiment JSON array found. Preview: {cleaned[:500]}")
                return self._default_sentiment_results(expected_count, parse_failed=True)

            parsed = json.loads(json_str)
            if not isinstance(parsed, list):
                return self._default_sentiment_results(expected_count, parse_failed=True)

            normalized = []
            for item in parsed[:expected_count]:
                if not isinstance(item, dict):
                    continue

                try:
                    score = float(item.get("score", 0.5))
                except (TypeError, ValueError):
                    score = 0.5

                sentiment = item.get("sentiment", "Neutral")
                if sentiment not in {"Positive", "Neutral", "Negative"}:
                    sentiment = "Neutral"

                normalized.append({
                    "score": max(0.0, min(1.0, score)),
                    "sentiment": sentiment,
                    "_parse_failed": False
                })

            if not normalized:
                return self._default_sentiment_results(expected_count, parse_failed=True)

            if len(normalized) < expected_count:
                normalized.extend(self._default_sentiment_results(
                    expected_count - len(normalized),
                    parse_failed=True
                ))

            return normalized

        except json.JSONDecodeError as e:
            preview = response_text[:500] if response_text else "EMPTY"
            _safe_print(f"[MiniMaxClient] Sentiment JSON decode error: {e}. Preview: {preview}")
            return self._default_sentiment_results(expected_count, parse_failed=True)

    def extract_intent_distribution(self, messages: List[str]) -> Dict[str, int]:
        prompt = f"""
请分析以下买家消息的意图类型，将每条消息分类到以下类型之一：
1. Pre-sale Inquiry (售前咨询) - 询问产品、价格、推荐、库存、款式等购买前问题
2. Post-sale Support (售后支持) - 收到产品后的问题反馈、退换货咨询、保修维修
3. Logistics (物流) - 关于发货、快递、物流跟踪、配送时间
4. Usage Guide (使用指南) - 询问如何使用、保养、功能说明
5. Complaint (投诉) - 仅限【明确投诉行为】：明确说"我要投诉"、"给差评"、"举报你"、"找经理"、"315投诉"等

【重要】Complaint判断标准（非常严格）：

一、只有满足以下条件才算投诉：
1. 明确的投诉行为词汇：投诉/差评/举报/315/消费者协会/工商/找经理
2. 明确的负面评价词：太差/质量差/很差/垃圾/骗子/假货/欺骗/失望/不满/态度差/服务差/恶心/坑人

二、以下情况【绝对不算投诉】：
- 询问性问题："有没有货""还有吗""就一个吗""什么时候发货"
- 表达疑惑："怎么买完就下架了""为什么没了""怎么回事"
- 功能性请求："退款""退货""换货""催发货"（无负面情绪词）
- 产品问题反馈（非负面）："小了""大了""不合适""发错货""颜色不对"
- 带语气词的询问："到底有没有货啊""怎么这样啊"（语气词≠不满）
- 物流咨询、库存咨询、价格咨询

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

只返回合法JSON对象，不要输出解释、Markdown代码块或思考过程。
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
            _safe_print(f"[MiniMaxClient] Error in intent analysis: {e}")
            return self._default_intent_distribution(parse_failed=True)

    def _parse_intent_response(self, response_text: str) -> Dict[str, int]:
        try:
            cleaned = self._clean_model_response(response_text)
            json_str = self._extract_json_value(cleaned, expected_type=dict)

            if not json_str:
                _safe_print(f"[MiniMaxClient] No intent JSON object found. Preview: {cleaned[:500]}")
                return self._default_intent_distribution(parse_failed=True)

            parsed = json.loads(json_str)
            if not isinstance(parsed, dict):
                return self._default_intent_distribution(parse_failed=True)

            result = self._default_intent_distribution(parse_failed=False)
            for key in self._intent_keys():
                try:
                    result[key] = int(parsed.get(key, 0))
                except (TypeError, ValueError):
                    result[key] = 0

            return result

        except json.JSONDecodeError as e:
            preview = response_text[:500] if response_text else "EMPTY"
            _safe_print(f"[MiniMaxClient] Intent JSON decode error: {e}. Preview: {preview}")
            return self._default_intent_distribution(parse_failed=True)

    def _default_sentiment_results(self, expected_count: int, parse_failed: bool) -> List[Dict[str, Any]]:
        return [
            {"score": 0.5, "sentiment": "Neutral", "_parse_failed": parse_failed}
            for _ in range(expected_count)
        ]

    def _default_intent_distribution(self, parse_failed: bool = False) -> Dict[str, Any]:
        result = {
            "Pre-sale Inquiry": 0,
            "Post-sale Support": 0,
            "Logistics": 0,
            "Usage Guide": 0,
            "Complaint": 0
        }
        result["_parse_failed"] = parse_failed
        return result

    def _intent_keys(self) -> List[str]:
        return [
            "Pre-sale Inquiry",
            "Post-sale Support",
            "Logistics",
            "Usage Guide",
            "Complaint"
        ]

    def _clean_model_response(self, response_text: str) -> str:
        if not response_text:
            return ""

        cleaned = re.sub(r"<think>.*?</think>", "", response_text, flags=re.DOTALL | re.IGNORECASE)
        cleaned = cleaned.strip()

        fence_match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL | re.IGNORECASE)
        if fence_match:
            cleaned = fence_match.group(1).strip()

        return cleaned

    def _extract_json_value(self, text: str, expected_type: type) -> str:
        opening, closing = ("[", "]") if expected_type is list else ("{", "}")
        decoder = json.JSONDecoder()

        for match in re.finditer(re.escape(opening), text):
            candidate = text[match.start():]
            try:
                value, end = decoder.raw_decode(candidate)
            except json.JSONDecodeError:
                continue

            if isinstance(value, expected_type):
                return candidate[:end]

        start = text.find(opening)
        end = text.rfind(closing) + 1
        if start != -1 and end > start:
            return text[start:end]

        return ""
