"""
Analyzer Orchestrator - 分析器编排器
实现多级降级策略：DeepSeek-R1 → DeepSeek-Chat → Zhipu GLM-4 → 规则引擎
"""
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any
from functools import lru_cache

from backend.ai.deepseek_client import DeepSeekClient
from backend.ai.zhipu_client import ZhipuClient
from backend.ai.rule_based_analyzer import RuleBasedAnalyzer
from backend.config import settings


class AnalyzerOrchestrator:
    """
    分析器编排器 - 实现多级降级策略

    L1: DeepSeek-R1（最优，深度推理）
    L2: DeepSeek-Chat（中等，快速分析）
    L3: Zhipu GLM-4.7（保底，原有系统）
    L4: 规则引擎（兜底，离线分析）
    """

    def __init__(self):
        """初始化所有分析器"""
        self.deepseek = None
        self.zhipu = None
        self.rule_based = RuleBasedAnalyzer()

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

    def analyze_buyer_persona(
        self,
        buyer_nick: str,
        profile: Dict,
        chats: List[Dict],
        orders: List[Dict]
    ) -> Dict[str, Any]:
        """
        多级降级分析策略

        **策略调整（基于聊天记录）**:
        - 有聊天记录 → DeepSeek-R1（深度分析聊天内容）
        - 无聊天记录 → Zhipu GLM-4（基于消费数据分析）

        Args:
            buyer_nick: 买家昵称
            profile: 客户档案（包含所有预计算表字段）
            chats: 聊天记录列表
            orders: 订单列表

        Returns:
            分析结果
        """
        # 检查缓存
        if settings.ai_enable_cache:
            cached = self._get_cached_analysis(buyer_nick, profile, chats)
            if cached:
                print(f"[Orchestrator] 缓存命中: {buyer_nick}")
                return cached

        # 关键判断：是否有聊天记录
        has_chats = chats and len(chats) > 0
        chat_count = len(chats) if has_chats else 0

        print(f"[Orchestrator] 分析 {buyer_nick}, 聊天记录数: {chat_count}")

        result = None

        # 策略1: 有聊天记录 → DeepSeek深度分析
        if has_chats and self.deepseek:
            try:
                print(f"[L1-DeepSeek] 使用DeepSeek-R1分析 {buyer_nick} (基于{chat_count}条聊天)")
                result = self.deepseek.analyze_buyer_persona(
                    buyer_nick, profile, chats, orders
                )
                result["analysis_method"] = "DeepSeek-R1"
                result["data_source"] = "聊天记录+消费数据"
                return self._cache_and_return(buyer_nick, profile, result)

            except TimeoutError:
                print(f"[L1→L2] DeepSeek超时，降级到Zhipu")
            except Exception as e:
                print(f"[L1→L2] DeepSeek失败: {e}，降级到Zhipu")

        # 策略2: 无聊天记录或DeepSeek失败 → Zhipu
        if self.zhipu:
            try:
                if has_chats:
                    print(f"[L2-Zhipu] 使用Zhipu分析 {buyer_nick} (DeepSeek降级)")
                else:
                    print(f"[L2-Zhipu] 使用Zhipu分析 {buyer_nick} (无聊天记录，基于消费数据)")

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
        for order in orders[:10]:  # 最多10条
            commodity = order.get("commodity_name", "未知商品")
            payment = order.get("payment", 0)
            time = order.get("pay_time", "")
            summary_lines.append(f"- {time}: {commodity} ¥{payment}")

        return "\n".join(summary_lines)

    def _get_cache_key(self, buyer_nick: str, profile: Dict) -> str:
        """生成缓存键"""
        # 使用buyer_nick + 关键字段生成hash
        key_data = {
            "buyer_nick": buyer_nick,
            "vip_level": profile.get("vip_level", ""),
            "l6m_netsales": profile.get("l6m_netsales", 0),
            "last_purchase_date": profile.get("last_purchase_date", "")
        }
        data_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()

    def _get_cached_analysis(
        self,
        buyer_nick: str,
        profile: Dict,
        chats: List[Dict]
    ) -> Dict:
        """
        获取缓存的分析结果

        简化实现：使用LRU缓存
        完整实现可以使用Redis
        """
        # 这里使用简化的内存缓存
        # 完整实现应该使用Redis或数据库
        return None

    def _cache_and_return(
        self,
        buyer_nick: str,
        profile: Dict,
        result: Dict
    ) -> Dict:
        """缓存结果并返回"""
        # 简化实现：实际应该存入Redis
        # 可以在这里实现缓存逻辑
        return result

    def clear_cache(self, buyer_nick: str = None):
        """清除缓存"""
        # 简化实现：实际应该清除Redis缓存
        pass


# 全局单例
_orchestrator_instance = None


def get_analyzer_orchestrator() -> AnalyzerOrchestrator:
    """获取分析器编排器单例"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = AnalyzerOrchestrator()
    return _orchestrator_instance
