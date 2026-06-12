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
from backend.ai.persona_context import build_persona_prompt_v3


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
        order_summary: str = "",
        orders: List[Dict[str, Any]] | None = None,
        is_incremental: bool = False
    ) -> Dict[str, Any]:
        prompt = build_persona_prompt_v3(user_nick, profile_data, recent_chats, orders or [], is_incremental=is_incremental)

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

**品类写作规则**
- 品类名保留英文原名，不要翻译成中文。
- 只有订单全部属于同一品类时，才可以写“历史订单均为某品类”或“100%为某品类”。
- 如果看到多个品类，必须写成多品类买家，不能把最高频品类写成全部订单。

【聊天记录】（最近{len(chats)}条）
{self._format_chats(chats[:20])}

**分析要求：**

1. **summary** - 画像总结（2-3句话）
   - 使用具体数字：客单价、退款率、复购间隔、品类占比、MD占比等
   - **深度推断**：
     * 品类偏好：如果多个品类并存，只能写最高频品类和占比，不能写成全部订单
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
        prompt = f"""
你是一位资深电商客户洞察专家。你的任务不是复述订单，而是提炼客户关键特征。

核心要求：
1. 使用具体数字和事实，不要用空泛形容词。
2. 不要逐单罗列订单，不要写流水账。
3. 结论必须聚焦三件事：购买时间习惯、品类偏好、价格/折扣心智。
4. 如果出现多个品类，要写成多品类客户，不允许把最高频品类写成全部订单。
5. 订单总数、总消费、AOV、折扣占比、折扣敏感度、购买高峰，优先使用下面事实包里的数字。

【买家事实包】
{order_summary}

【聊天记录】（最近{len(chats)}条）
{self._format_chats(chats[:20])}

写作要求：
- summary：2-3句话，必须写出客户关键特征，不要写成流水账。
- key_interests：3-5个，提炼稳定偏好和行为习惯。
- pain_points：2-4个，只写真实可见的阻碍或风险。
- recommended_action：1-2句话，给出下一步跟进动作。

可用结论方向：
- 购买高峰期是否集中在 5-6 月、10-12 月等大促节点。
- 是否是价格敏感客户，是否集中买折扣/MD商品。
- 是否偏好某类商品、是否稳定复购同类。
- 是否存在阶段性爆发购买、长间隔回购。

输出格式（纯JSON）：
{{
  "summary": "用关键特征总结客户，不要复述订单",
  "key_interests": ["兴趣点1", "兴趣点2"],
  "pain_points": ["痛点1", "痛点2"],
  "recommended_action": "下一步跟进建议"
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
                    "summary": cleaned[:220],
                    "key_interests": [],
                    "pain_points": [],
                    "recommended_action": "请根据买家情况制定跟进策略"
                }

        except json.JSONDecodeError as e:
            _safe_print(f"[MiniMaxClient] JSON decode error: {e}")
            return {
                "summary": response_text[:220] if response_text else "AI分析失败",
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

    def analyze_sentiment_intent(
        self,
        buyer_nick: str,
        messages: List[str],
        is_incremental: bool = False
    ) -> Dict[str, Any]:
        """
        分析客户消息的情感和意图（统一接口 - 与 DeepSeek 同签名同字段）

        用途：
        - 上层 batch_analyzer 调用的统一入口，L1=MiniMax（首选，月订阅制省 token），L2=DeepSeek（备选，按 token 计费）。
        - Prompt 与 DeepSeek 完全一致（deepseek_client.py:854-934），保证两个模型行为一致。
        - 返回字段与 DeepSeek 完全对齐：sentiment_score / sentiment_label / intent_distribution / dominant_intent / complaint_count。

        Args:
            buyer_nick: 买家昵称
            messages: 客户消息列表（仅买家自己说的话）
            is_incremental: 是否增量分析模式。True 时 prompt 强调"新增聊天"。

        Returns:
            {
                "sentiment_score": float (0-1, 0=非常消极, 1=非常积极),
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

        # Prompt 与 DeepSeek 完全一致（deepseek_client.py:854-934）— 一字不改，确保行为对齐
        scope_hint = (
            "以下是**自上次分析以来的新增聊天**。"
            if is_incremental
            else ""
        )

        prompt = f"""分析以下客户消息的情感和意图。{scope_hint}

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

一、Neutral（0.4-0.6）：正常的业务咨询（最常见）
- 询问库存、价格、物流："有没有货""什么时候发货""多少钱"
- 表达疑惑或好奇："怎么下架了""就一个吗""为什么"
- 功能性请求："退款""退货""换货"
- 产品问题反馈（非投诉）："小了""大了""不合适""颜色不对""发错货"
- 正常售后沟通："好的""可以""收到"等礼貌回复
- 带语气词的询问："到底有没有啊""怎么这样"（语气词≠负面情绪）

二、Negative（< 0.4）：只有明确负面表达时才判为负面
- 包含投诉词汇："我要投诉""给差评""举报"
- 包含负面评价词："太差""垃圾""骗子""假货""失望""不满"
- 表达愤怒或强烈不满

三、Positive（> 0.6）：明确的正面情绪
- 表达感谢、满意、赞赏
- 再次购买意愿、推荐他人

【重要】意图分类标准（每条消息必须归入以下5类之一）：

1. Pre-sale Inquiry（售前咨询）- 询问产品、价格、推荐、库存、款式等购买前问题
   - 关键词：推荐、有没有货、多少钱、尺寸、颜色、款式、新款、上市、材质、面料、有没有、现货
   - ✅ "推荐一款春季外套" → Pre-sale Inquiry
   - ✅ "这个有没有L码" → Pre-sale Inquiry
   - ✅ "新款什么时候上架" → Pre-sale Inquiry
   - ✅ "这件和那件有什么区别" → Pre-sale Inquiry

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

【重要】intent_distribution 的数值 = 属于该类别的消息条数（不是分数），所有类别的数值之和应等于消息总数。

【示例】：
- "推荐一款春季外套" → Neutral(0.5), Pre-sale Inquiry
- "这个有没有现货" → Neutral(0.5), Pre-sale Inquiry
- "质量太差了" → Negative(0.2), Complaint
- "我要投诉你们" → Negative(0.2), Complaint
- "小了，我要退货" → Neutral(0.5), Post-sale Support（正常退货≠投诉）
- "发错货了，帮我换一下" → Neutral(0.5), Post-sale Support（正常售后≠投诉）
- "什么时候发货" → Neutral(0.5), Logistics
- "好的👌" → Neutral(0.6), Post-sale Support（礼貌确认）

只返回JSON，不要其他内容。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
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
            return self._parse_sentiment_intent_response(result_text)

        except Exception as e:
            _safe_print(f"[MiniMax] 情感意图分析失败: {e}")
            raise

    def _parse_sentiment_intent_response(self, response_text: str) -> Dict[str, Any]:
        """解析情感意图分析响应（与 DeepSeek._parse_sentiment_response 字段对齐）"""
        try:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1

            if start != -1 and end > start:
                json_str = response_text[start:end]
                result = json.loads(json_str)

                # 确保所有必要字段存在（与 DeepSeek 完全一致）
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
            _safe_print(f"[MiniMax] 情感意图JSON解析失败: {e}")
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

    def analyze_sentiment_batch(
        self,
        messages: List[str],
        is_incremental: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Analyze sentiment for a batch of buyer messages.

        Args:
            messages: 买家消息内容列表
            is_incremental: True=增量模式（messages 是自上次分析以来的新聊天）；
                          False=全量模式（messages 是买家全部历史聊天）。
        """
        if not messages:
            return []

        scope_hint = (
            "以下是**自上次分析以来的新增聊天**。请仅基于以下新增聊天判断情感倾向，不要考虑之前的历史聊天。"
            if is_incremental
            else "以下是买家的全部历史聊天。请基于全部历史聊天判断每条消息的情感倾向。"
        )

        prompt = f"""
{scope_hint}

对每条消息给出：
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
            return self._heuristic_sentiment_results(messages, source="exception")

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
            return self._parse_intent_response(response_text, messages)

        except Exception as e:
            _safe_print(f"[MiniMaxClient] Error in intent analysis: {e}")
            return self._heuristic_intent_distribution(messages, source="exception")

    def _parse_intent_response(self, response_text: str, messages: List[str]) -> Dict[str, int]:
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
                    result[key] = int(self._lookup_intent_value(parsed, key))
                except (TypeError, ValueError):
                    result[key] = 0

            if sum(result[k] for k in self._intent_keys()) == 0:
                _safe_print("[MiniMaxClient] Parsed intent distribution is empty; falling back to heuristic classification")
                return self._heuristic_intent_distribution(messages, source="empty_model")

            return result

        except json.JSONDecodeError as e:
            preview = response_text[:500] if response_text else "EMPTY"
            _safe_print(f"[MiniMaxClient] Intent JSON decode error: {e}. Preview: {preview}")
            return self._default_intent_distribution(parse_failed=True)

    def _heuristic_sentiment_results(self, messages: List[str], source: str = "heuristic") -> List[Dict[str, Any]]:
        results = []
        for msg in messages:
            text = (msg or "").lower()
            positive_hits = sum(1 for word in ["好", "喜欢", "满意", "感谢", "谢谢", "不错", "很好", "棒", "赞"] if word in text)
            negative_hits = sum(1 for word in ["差", "不好", "失望", "投诉", "退货", "退款", "问题", "坏", "不喜欢"] if word in text)

            if negative_hits > positive_hits:
                sentiment = "Negative"
                score = 0.2
            elif positive_hits > negative_hits:
                sentiment = "Positive"
                score = 0.8
            else:
                sentiment = "Neutral"
                score = 0.5

            results.append({
                "score": score,
                "sentiment": sentiment,
                "_parse_failed": False,
                "_source": source
            })
        return results

    def _heuristic_intent_distribution(self, messages: List[str], source: str = "heuristic") -> Dict[str, int]:
        all_text = " ".join(messages)

        pre_sale_keywords = ['价格', '多少钱', '有货', '尺寸', '颜色', '款式', '推荐', '新款', '上市']
        post_sale_keywords = ['退货', '换货', '维修', '保修', '发票', '物流', '快递', '收到']
        strong_complaint_keywords = ['投诉', '差评', '举报', '315', '消费者协会', '工商', '找经理']
        dissatisfaction_keywords = [
            '太差', '质量差', '很差', '垃圾', '骗子', '骗人', '假的', '假货', '欺骗',
            '失望', '不满', '不满意', '太慢', '态度差', '服务差', '差的', '不好用',
            '质量太差', '质量不好', '做工差', '掉色', '褪色', '破损', '坏了', '有问题',
            '差劲', '太差了', '质量太差了', '差评', '给差评'
        ]
        functional_keywords = ['退款', '退货', '换货', '催促', '发货', '收到货', '物流']

        pre_sale_count = sum(1 for word in pre_sale_keywords if word in all_text)
        post_sale_count = sum(1 for word in post_sale_keywords if word in all_text)

        strong_matches = [kw for kw in strong_complaint_keywords if kw in all_text]
        dissatisfaction_matches = [kw for kw in dissatisfaction_keywords if kw in all_text]
        functional_matches = [kw for kw in functional_keywords if kw in all_text]

        complaint_count = 0
        if len(strong_matches) >= 1:
            complaint_count = 1
        elif len(dissatisfaction_matches) >= 1:
            complaint_count = 1

        result = {
            "Pre-sale Inquiry": pre_sale_count,
            "Post-sale Support": post_sale_count,
            "Logistics": 0,
            "Usage Guide": 0,
            "Complaint": complaint_count,
            "_parse_failed": False,
            "_source": source
        }

        if pre_sale_count == 0 and post_sale_count == 0 and complaint_count == 0 and functional_matches:
            # 常见正常售后场景：退款/退货/发货
            result["Post-sale Support"] = 1

        return result

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

    def _lookup_intent_value(self, parsed: Dict[str, Any], canonical_key: str) -> Any:
        aliases = {
            "Pre-sale Inquiry": [
                "Pre-sale Inquiry", "Pre-sale", "Pre Sale", "Presale", "pre_sale",
                "preSale", "售前咨询", "售前", "咨询", "购买咨询"
            ],
            "Post-sale Support": [
                "Post-sale Support", "Post-sale", "Post Sale", "After-sale", "After Sales",
                "post_sale", "postSale", "售后支持", "售后", "售后服务"
            ],
            "Logistics": [
                "Logistics", "Shipping", "Delivery", "logistics", "shipping",
                "物流", "发货", "配送", "快递"
            ],
            "Usage Guide": [
                "Usage Guide", "Usage", "Guide", "How-to", "usage_guide",
                "使用指南", "使用", "教程", "保养", "功能说明"
            ],
            "Complaint": [
                "Complaint", "Complaints", "complaint", "投诉", "差评", "负面反馈"
            ],
        }

        normalized = {self._normalize_key(key): value for key, value in parsed.items()}
        for alias in aliases[canonical_key]:
            value = normalized.get(self._normalize_key(alias))
            if value is not None:
                return value
        return 0

    def _normalize_key(self, key: Any) -> str:
        return re.sub(r"[\s_\-]+", "", str(key).strip().lower())

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
