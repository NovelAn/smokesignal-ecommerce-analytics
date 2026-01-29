"""
Rule-Based Analyzer - 规则引擎兜底分析
当AI模型不可用时使用规则进行客户画像分析
"""
from typing import Dict, List, Any
from backend.ai.data_extractor import detect_rookie_signal, detect_expert_signal


class RuleBasedAnalyzer:
    """基于规则的客户画像分析器（兜底方案）"""

    def analyze(
        self,
        profile: Dict,
        chats: List[Dict],
        orders: List[Dict]
    ) -> Dict[str, Any]:
        """
        使用规则分析客户画像

        Args:
            profile: 客户档案
            chats: 聊天记录
            orders: 订单列表

        Returns:
            {
                "summary": str,
                "key_interests": List[str],
                "pain_points": List[str],
                "recommended_action": str,
                "confidence_level": "中/低"
            }
        """
        # 统计信号
        rookie_count = sum(1 for chat in chats if detect_rookie_signal(chat.get("content", "")))
        expert_count = sum(1 for chat in chats if detect_expert_signal(chat.get("content", "")))

        # VIP等级
        vip_level = profile.get("vip_level", "Non-VIP")
        city = profile.get("city", "")
        l6m_netsales = profile.get("l6m_netsales", 0) or 0
        l1y_netsales = profile.get("l1y_netsales", 0) or 0

        # 退款率
        l6m_refund_rate = profile.get("l6m_refund_rate", 0) or 0

        # 根据信号判断类型
        if rookie_count >= 3:
            return self._analyze_rookie(profile, chats, orders)
        elif expert_count >= 3:
            return self._analyze_expert(profile, chats, orders)
        elif l6m_refund_rate > 0.1:
            return self._analyze_quality_sensitive(profile, chats, orders)
        elif vip_level in ["V3", "V2"]:
            return self._analyze_high_value(profile, chats, orders)
        else:
            return self._analyze_regular(profile, chats, orders)

    def _analyze_rookie(
        self,
        profile: Dict,
        chats: List[Dict],
        orders: List[Dict]
    ) -> Dict[str, Any]:
        """分析新手客户"""
        city = profile.get("city", "")
        top_category = profile.get("top_category", "")

        return {
            "summary": f"{city}的新手客户，对{top_category}缺乏了解，需要详细的产品指导和推荐建议。根据聊天记录显示多次表达'不懂'、'求推荐'等新手信号。",
            "key_interests": [
                "产品基础知识学习",
                "使用入门指导",
                "适合新手的产品推荐",
                "简单的操作教程"
            ],
            "pain_points": [
                "缺乏产品认知和了解",
                "不知道如何选择适合自己的产品",
                "担心买错或不适合",
                "需要耐心解答基础问题"
            ],
            "recommended_action": "主动提供新手入门指南，推荐适合新手的产品，耐心解答基础问题，建立信任感",
            "confidence_level": "中"
        }

    def _analyze_expert(
        self,
        profile: Dict,
        chats: List[Dict],
        orders: List[Dict]
    ) -> Dict[str, Any]:
        """分析专家客户"""
        city = profile.get("city", "")
        vip_level = profile.get("vip_level", "Non-VIP")
        l1y_netsales = profile.get("l1y_netsales", 0) or 0

        return {
            "summary": f"{city}的{vip_level}资深客户，历史消费¥{l1y_netsales:,.0f}，对产品有深入了解，关注专业细节和工艺。根据聊天记录使用专业术语询问参数、工艺等。",
            "key_interests": [
                "高端产品和稀有品牌",
                "专业工艺和材质细节",
                "产品对比和性能参数",
                "新品和专业定制"
            ],
            "pain_points": [
                "高端产品稀缺性难满足",
                "个性化需求难以匹配",
                "新品更新速度慢",
                "缺乏深度专业交流"
            ],
            "recommended_action": "推荐高端新品，提供专业细节对比，满足定制化需求，建立专业顾问形象",
            "confidence_level": "中"
        }

    def _analyze_quality_sensitive(
        self,
        profile: Dict,
        chats: List[Dict],
        orders: List[Dict]
    ) -> Dict[str, Any]:
        """分析品质敏感客户"""
        city = profile.get("city", "")
        l6m_refund_rate = profile.get("l6m_refund_rate", 0) or 0
        total_refund_count = profile.get("total_refund_count", 0) or 0

        return {
            "summary": f"{city}的品质敏感客户，退款率{l6m_refund_rate:.1%}（{total_refund_count}次），对产品质量要求严格，追求完美体验。",
            "key_interests": [
                "正品保障和品质验证",
                "品牌信誉和产品口碑",
                "质量认证和检验报告",
                "高端品质产品"
            ],
            "pain_points": [
                "对产品真伪有疑虑",
                "对品质要求高，容易不满意",
                "担心买到劣质产品",
                "需要品质保证"
            ],
            "recommended_action": "强调正品保障，提供质量认证，推荐高端品质产品，建立品质信任",
            "confidence_level": "中"
        }

    def _analyze_high_value(
        self,
        profile: Dict,
        chats: List[Dict],
        orders: List[Dict]
    ) -> Dict[str, Any]:
        """分析高价值客户"""
        city = profile.get("city", "")
        vip_level = profile.get("vip_level", "Non-VIP")
        l1y_netsales = profile.get("l1y_netsales", 0) or 0
        l6m_netsales = profile.get("l6m_netsales", 0) or 0

        return {
            "summary": f"{city}的{vip_level}高价值客户，历史消费¥{l1y_netsales:,.0f}，最近6个月消费¥{l6m_netsales:,.0f}，忠诚度高，是核心客户群体。",
            "key_interests": [
                "高端产品和VIP服务",
                "新品优先体验",
                "定制化和专属服务",
                "品牌价值和品质保障"
            ],
            "pain_points": [
                "期望获得VIP专属待遇",
                "希望得到更快速的服务响应",
                "对新品和稀缺产品有需求",
                "追求卓越体验"
            ],
            "recommended_action": "提供VIP专属服务，优先推荐新品，定期关怀回访，建立长期合作关系",
            "confidence_level": "中"
        }

    def _analyze_regular(
        self,
        profile: Dict,
        chats: List[Dict],
        orders: List[Dict]
    ) -> Dict[str, Any]:
        """分析普通客户"""
        city = profile.get("city", "")
        l6m_netsales = profile.get("l6m_netsales", 0) or 0

        # 检查是否有聊天记录
        has_chats = len(chats) > 0
        chat_evidence = "根据聊天记录" if has_chats else "暂无聊天记录"

        return {
            "summary": f"{city}客户，最近6个月消费¥{l6m_netsales:,.0f}。{chat_evidence}{'有一定互动' if has_chats else '，缺乏充分信息'}。",
            "key_interests": [
                "产品购买和使用",
                "价格和优惠信息"
            ],
            "pain_points": [
                "数据不足，无法准确推断",
                "需要更多互动了解需求"
            ],
            "recommended_action": "根据客户具体情况制定跟进策略，主动沟通了解需求",
            "confidence_level": "低"
        }
