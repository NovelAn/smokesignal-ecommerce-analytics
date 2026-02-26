"""
Analyzer Orchestrator - 分析器编排器
实现多级降级策略：DeepSeek-V3.2 → Zhipu GLM-4.7 → 规则引擎

缓存策略: 纯增量更新，无TTL
- 存储数据快照 (analyzed_last_purchase_date, analyzed_last_chat_date)
- 只有新订单/新聊天才触发重新分析

Fallback触发条件：
- 429 错误 (API余额不足/Rate Limit)
- Timeout 超时
- 其他API异常
"""
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional

from backend.ai.deepseek_client import DeepSeekClient
from backend.ai.zhipu_client import ZhipuClient
from backend.ai.rule_based_analyzer import RuleBasedAnalyzer
from backend.config import settings


class AICacheManager:
    """AI 分析结果缓存管理器 - 纯增量更新，无TTL"""

    def __init__(self):
        from backend.database import Database
        self.db = Database()

    def get(self, buyer_nick: str) -> Optional[Dict]:
        """
        获取缓存

        Returns:
            缓存数据，包含数据快照和画像分析结果
        """
        try:
            query = """
                SELECT
                    persona_summary, persona_key_interests, persona_pain_points,
                    persona_recommended_action, persona_method,
                    persona_analyzed_at, persona_analyzed_last_purchase_date, persona_analyzed_last_chat_date,
                    sentiment_score, sentiment_label, dominant_intent,
                    sentiment_analyzed_at, sentiment_analyzed_last_chat_date
                FROM buyer_ai_analysis_cache
                WHERE buyer_nick = %s
            """
            results = self.db.execute_query(query, (buyer_nick,))

            if results:
                row = results[0]
                return {
                    # 画像分析结果
                    "persona_summary": row.get("persona_summary", ""),
                    "persona_key_interests": json.loads(row.get("persona_key_interests") or "[]"),
                    "persona_pain_points": json.loads(row.get("persona_pain_points") or "[]"),
                    "persona_recommended_action": row.get("persona_recommended_action", ""),
                    "persona_method": row.get("persona_method", ""),
                    # 画像分析时间戳（独立）
                    "persona_analyzed_at": row.get("persona_analyzed_at"),
                    "persona_analyzed_last_purchase_date": row.get("persona_analyzed_last_purchase_date"),
                    "persona_analyzed_last_chat_date": row.get("persona_analyzed_last_chat_date"),
                    # 情感分析结果
                    "sentiment_score": row.get("sentiment_score"),
                    "sentiment_label": row.get("sentiment_label"),
                    "dominant_intent": row.get("dominant_intent"),
                    # 情感分析时间戳（独立）
                    "sentiment_analyzed_at": row.get("sentiment_analyzed_at"),
                    "sentiment_analyzed_last_chat_date": row.get("sentiment_analyzed_last_chat_date"),
                }
            return None
        except Exception as e:
            print(f"[AICacheManager] 获取缓存失败: {e}")
            return None

    def set_persona(self, buyer_nick: str, result: Dict, profile: Dict):
        """
        保存画像分析结果 + 数据快照

        使用 INSERT ... ON DUPLICATE KEY UPDATE 支持部分更新
        """
        try:
            # 获取当前数据快照
            last_purchase = profile.get("last_purchase_date")
            last_chat = profile.get("last_chat_date")

            insert_sql = """
                INSERT INTO buyer_ai_analysis_cache (
                    buyer_nick,
                    persona_summary, persona_key_interests, persona_pain_points,
                    persona_recommended_action, persona_method,
                    persona_analyzed_at, persona_analyzed_last_purchase_date, persona_analyzed_last_chat_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    persona_summary = VALUES(persona_summary),
                    persona_key_interests = VALUES(persona_key_interests),
                    persona_pain_points = VALUES(persona_pain_points),
                    persona_recommended_action = VALUES(persona_recommended_action),
                    persona_method = VALUES(persona_method),
                    persona_analyzed_at = VALUES(persona_analyzed_at),
                    persona_analyzed_last_purchase_date = VALUES(persona_analyzed_last_purchase_date),
                    persona_analyzed_last_chat_date = VALUES(persona_analyzed_last_chat_date),
                    updated_at = CURRENT_TIMESTAMP
            """
            self.db.execute_update(insert_sql, (
                buyer_nick,
                result.get("summary", ""),
                json.dumps(result.get("key_interests", []), ensure_ascii=False),
                json.dumps(result.get("pain_points", []), ensure_ascii=False),
                result.get("recommended_action", ""),
                result.get("analysis_method", ""),
                datetime.now(),
                last_purchase,
                last_chat
            ))
            print(f"[AICacheManager] 画像缓存已保存: {buyer_nick}")
        except Exception as e:
            print(f"[AICacheManager] 保存画像缓存失败: {e}")

    def clear_persona(self, buyer_nick: str):
        """清除画像缓存（保留情感缓存）"""
        try:
            sql = """
                UPDATE buyer_ai_analysis_cache
                SET persona_summary = NULL,
                    persona_key_interests = NULL,
                    persona_pain_points = NULL,
                    persona_recommended_action = NULL,
                    persona_method = NULL
                WHERE buyer_nick = %s
            """
            self.db.execute_update(sql, (buyer_nick,))
            print(f"[AICacheManager] 画像缓存已清除: {buyer_nick}")
        except Exception as e:
            print(f"[AICacheManager] 清除画像缓存失败: {e}")

    def clear_sentiment(self, buyer_nick: str):
        """清除情感缓存（保留画像缓存）"""
        try:
            sql = """
                UPDATE buyer_ai_analysis_cache
                SET sentiment_score = NULL,
                    sentiment_label = NULL,
                    intent_distribution = NULL,
                    dominant_intent = NULL,
                    pre_sale_keywords = NULL,
                    post_sale_keywords = NULL,
                    complaint_count = 0,
                    sentiment_method = NULL
                WHERE buyer_nick = %s
            """
            self.db.execute_update(sql, (buyer_nick,))
            print(f"[AICacheManager] 情感缓存已清除: {buyer_nick}")
        except Exception as e:
            print(f"[AICacheManager] 清除情感缓存失败: {e}")

    def clear_all(self, buyer_nick: str = None):
        """清除全部缓存"""
        try:
            if buyer_nick:
                sql = "DELETE FROM buyer_ai_analysis_cache WHERE buyer_nick = %s"
                self.db.execute_update(sql, (buyer_nick,))
            else:
                sql = "TRUNCATE TABLE buyer_ai_analysis_cache"
                self.db.execute_update(sql)
            print(f"[AICacheManager] 缓存已清除: {buyer_nick or '全部'}")
        except Exception as e:
            print(f"[AICacheManager] 清除缓存失败: {e}")


class AnalyzerOrchestrator:
    """
    分析器编排器 - 实现多级降级策略

    L1: DeepSeek-V3.2（主模型）
        - 有聊天记录 → deepseek-reasoner（深度推理）
        - 无聊天记录 → deepseek-chat（快速分析）

    L2: Zhipu GLM-4.7（备选模型 - DeepSeek失败时降级）
        - 429错误（余额不足）时触发
        - Timeout时触发
        - 其他API异常时触发

    L3: 规则引擎（兜底 - 所有AI模型失败时）

    缓存策略: 纯增量更新
    - 只有新订单/新聊天才触发重新分析
    - 无TTL过期机制
    """

    def __init__(self):
        """初始化所有分析器"""
        self.deepseek = None
        self.zhipu = None
        self.rule_based = RuleBasedAnalyzer()
        self.cache_manager = None

        # 延迟初始化AI客户端（需要API key）
        try:
            if settings.deepseek_api_key:
                self.deepseek = DeepSeekClient()
                print("[Orchestrator] DeepSeek客户端初始化成功")
        except Exception as e:
            print(f"[Orchestrator] DeepSeek初始化失败: {e}")

        try:
            if settings.zhipu_api_key:
                self.zhipu = ZhipuClient()
                print("[Orchestrator] Zhipu客户端初始化成功")
        except Exception as e:
            print(f"[Orchestrator] Zhipu初始化失败: {e}")

        # 初始化缓存管理器
        try:
            if settings.ai_enable_cache:
                self.cache_manager = AICacheManager()
                print("[Orchestrator] AI缓存管理器初始化成功")
        except Exception as e:
            print(f"[Orchestrator] AI缓存管理器初始化失败: {e}")

    def should_update_persona(self, buyer_nick: str, profile: Dict) -> bool:
        """
        判断是否需要更新AI客户画像

        触发条件 (满足任一):
        1. 从未分析过 (缓存不存在或 persona_summary 为空)
        2. 有新增订单 (last_purchase_date > persona_analyzed_last_purchase_date)
        3. 有新增聊天记录 (last_chat_date > persona_analyzed_last_chat_date)
        """
        if not self.cache_manager:
            return True  # 无缓存管理器，总是分析

        cache = self.cache_manager.get(buyer_nick)

        if not cache or not cache.get("persona_summary"):
            return True  # 首次分析

        # 有新订单？
        current_last_purchase = profile.get("last_purchase_date")
        cached_last_purchase = cache.get("persona_analyzed_last_purchase_date")
        if current_last_purchase and cached_last_purchase:
            if self._compare_dates(current_last_purchase, cached_last_purchase) > 0:
                return True

        # 有新聊天？
        current_last_chat = profile.get("last_chat_date")
        cached_last_chat = cache.get("persona_analyzed_last_chat_date")
        if current_last_chat and cached_last_chat:
            if self._compare_dates(current_last_chat, cached_last_chat) > 0:
                return True

        return False

    def _compare_dates(self, date1, date2) -> int:
        """比较两个日期，返回 1(date1>date2), 0(相等), -1(date1<date2)"""
        # 统一转换为标准格式字符串进行比较
        def normalize_date_str(d):
            if d is None:
                return ""
            # datetime 对象 - 使用 str() 保持与数据库一致
            if hasattr(d, 'isoformat'):
                return str(d)  # 使用 str() 而不是 isoformat() 保持格式一致
            # 已经是字符串 - 标准化 T 为空格
            if isinstance(d, str):
                return d.replace('T', ' ')
            # 其他类型 - 转字符串
            return str(d)

        str1 = normalize_date_str(date1)
        str2 = normalize_date_str(date2)

        if str1 > str2:
            return 1
        elif str1 < str2:
            return -1
        return 0

    def analyze_buyer_persona(
        self,
        buyer_nick: str,
        profile: Dict,
        chats: List[Dict],
        orders: List[Dict],
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        多级降级分析策略

        Args:
            buyer_nick: 买家昵称
            profile: 客户档案（包含所有预计算表字段）
            chats: 聊天记录列表
            orders: 订单列表
            force_refresh: 是否强制刷新（忽略缓存）

        Returns:
            分析结果
        """
        import sys

        # 检查是否需要更新
        if not force_refresh and settings.ai_enable_cache:
            if not self.should_update_persona(buyer_nick, profile):
                # 返回缓存结果
                cache = self.cache_manager.get(buyer_nick)
                if cache:
                    print(f"[Orchestrator] 缓存命中，跳过分析: {buyer_nick}")
                    return {
                        "summary": cache.get("persona_summary", ""),
                        "key_interests": cache.get("persona_key_interests", []),
                        "pain_points": cache.get("persona_pain_points", []),
                        "recommended_action": cache.get("persona_recommended_action", ""),
                        "analysis_method": cache.get("persona_method", ""),
                        "from_cache": True
                    }

        # 关键判断：是否有聊天记录
        has_chats = chats and len(chats) > 0
        chat_count = len(chats) if has_chats else 0
        order_count = len(orders) if orders else 0

        print(f"[Orchestrator] 分析 {buyer_nick}, 聊天记录数: {chat_count}, 订单数: {order_count}", file=sys.stderr)

        result = None

        # 策略1: DeepSeek深度分析（优先使用）
        if self.deepseek:
            try:
                if has_chats:
                    print(f"[L1-DeepSeek-R1] 使用DeepSeek-Reasoner分析 {buyer_nick} (基于{chat_count}条聊天)")
                    result = self.deepseek.analyze_buyer_persona(
                        buyer_nick, profile, chats, orders
                    )
                    result["analysis_method"] = "DeepSeek-R1"
                    result["data_source"] = "聊天记录+消费数据"
                else:
                    print(f"[L1-DeepSeek-Chat] 使用DeepSeek-Chat分析 {buyer_nick} (基于消费数据)")
                    result = self.deepseek.analyze_buyer_persona_chat(
                        buyer_nick, profile, chats, orders
                    )
                    result["analysis_method"] = "DeepSeek-Chat"
                    result["data_source"] = "消费数据"

                return self._cache_and_return(buyer_nick, profile, result)

            except TimeoutError:
                print(f"[L1→L2] DeepSeek超时，降级到Zhipu GLM-4.7")
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "rate" in error_str or "quota" in error_str or "insufficient" in error_str or "余额" in error_str:
                    print(f"[L1→L2] DeepSeek API余额不足(429)，降级到Zhipu GLM-4.7")
                else:
                    print(f"[L1→L2] DeepSeek失败: {e}，降级到Zhipu GLM-4.7")

        # 策略2: Zhipu GLM-4.7（DeepSeek失败时降级）
        if self.zhipu:
            try:
                if has_chats:
                    print(f"[L2-Zhipu-GLM4.7] 使用Zhipu分析 {buyer_nick} (Fallback)")
                else:
                    print(f"[L2-Zhipu-GLM4.7] 使用Zhipu分析 {buyer_nick} (Fallback，基于消费数据)")

                result = self.zhipu.analyze_buyer_persona(
                    buyer_nick,
                    profile,
                    chats,
                    self._format_order_summary(orders)
                )
                result["analysis_method"] = "Zhipu-GLM"
                result["data_source"] = "消费数据" if not has_chats else "聊天记录+消费数据(降级)"
                return self._cache_and_return(buyer_nick, profile, result)

            except Exception as e:
                print(f"[L2→L3] Zhipu失败: {e}，使用规则引擎")

        # 策略3: 规则引擎兜底
        print(f"[L3-Rule] 使用规则引擎分析 {buyer_nick}")
        result = self.rule_based.analyze(profile, chats, orders)
        result["analysis_method"] = "Rule-Based"
        result["data_source"] = "规则引擎"
        return self._cache_and_return(buyer_nick, profile, result)

    def _format_order_summary(self, orders: List[Dict]) -> str:
        """格式化订单摘要（用于Zhipu）"""
        if not orders:
            return "暂无订单记录"

        summary_lines = []
        for order in orders[:10]:
            commodity = order.get("commodity_name", "未知商品")
            payment = order.get("payment", 0)
            time = order.get("pay_time", "")
            summary_lines.append(f"- {time}: {commodity} ¥{payment}")

        return "\n".join(summary_lines)

    def _cache_and_return(
        self,
        buyer_nick: str,
        profile: Dict,
        result: Dict
    ) -> Dict:
        """
        缓存结果并返回
        """
        if self.cache_manager:
            # 检查是否为有效的分析结果
            is_valid_result = self._is_valid_analysis(result)

            if is_valid_result:
                self.cache_manager.set_persona(buyer_nick, result, profile)
            else:
                print(f"[Orchestrator] 跳过缓存: 分析结果无效")

        return result

    def _is_valid_analysis(self, result: Dict) -> bool:
        """检查分析结果是否有效"""
        if not result:
            return False

        summary = result.get("summary", "")

        # 检查是否为默认失败响应或AI拒绝分析的响应
        invalid_summaries = [
            "暂无AI分析",
            "AI分析暂时不可用",
            "AI分析失败",
            "无法进行客户洞察分析",  # DeepSeek拒绝分析时的响应
            "未包含任何有效的客户聊天记录",  # 数据不足时的响应
            "证据中未包含",  # 证据不足时的响应
            "无法分析",  # 通用拒绝响应
            "无法提取"  # 提取失败响应
        ]

        for invalid in invalid_summaries:
            if invalid in summary:
                return False

        # 至少要有有效的 summary 或 interests/pain_points
        has_valid_content = (
            summary and len(summary) > 20 and "暂无" not in summary
        ) or (
            result.get("key_interests") and len(result.get("key_interests", [])) > 0
        ) or (
            result.get("pain_points") and len(result.get("pain_points", [])) > 0
        )

        return has_valid_content

    def force_refresh(self, buyer_nick: str):
        """强制刷新画像缓存"""
        if self.cache_manager:
            self.cache_manager.clear_persona(buyer_nick)
            print(f"[Orchestrator] 已清除画像缓存，下次将重新分析: {buyer_nick}")

    def clear_cache(self, buyer_nick: str = None):
        """清除缓存"""
        if self.cache_manager:
            self.cache_manager.clear_all(buyer_nick)
            print(f"[Orchestrator] 缓存已清除: {buyer_nick or '全部'}")


# 全局单例
_orchestrator_instance = None


def get_analyzer_orchestrator() -> AnalyzerOrchestrator:
    """获取分析器编排器单例"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = AnalyzerOrchestrator()
    return _orchestrator_instance
