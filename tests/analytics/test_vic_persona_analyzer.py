import pytest
from backend.analytics.vic_persona_analyzer import VicPersonaAnalyzer


class TestAggregateInterests:
    """VIC key_interests 聚合测试"""

    def test_aggregate_key_interests(self):
        """测试从多个 VIC 客户聚合 key_interests"""
        analyzer = VicPersonaAnalyzer()
        mock_personas = [
            {"buyer_nick": "vic1", "key_interests": ["高端烟斗收藏", "限量版产品"]},
            {"buyer_nick": "vic2", "key_interests": ["高端烟斗收藏", "奢侈品消费"]},
            {"buyer_nick": "vic3", "key_interests": ["限量版产品", "品牌忠诚度高"]},
        ]
        result = analyzer.aggregate_interests(mock_personas)
        assert result[0]["keyword"] == "高端烟斗收藏"
        assert result[0]["count"] == 2
        assert result[0]["percentage"] == pytest.approx(66.7, abs=0.1)

    def test_aggregate_interests_handles_json_string(self):
        """key_interests 可能是 JSON 字符串（DB 存储格式）"""
        analyzer = VicPersonaAnalyzer()
        mock_personas = [
            {"buyer_nick": "vic1", "key_interests": '["高端烟斗", "限量版"]'},
        ]
        result = analyzer.aggregate_interests(mock_personas)
        assert len(result) == 2

    def test_aggregate_interests_empty(self):
        """空列表应返回空结果"""
        analyzer = VicPersonaAnalyzer()
        result = analyzer.aggregate_interests([])
        assert result == []

    def test_aggregate_interests_missing_field(self):
        """key_interests 字段缺失时应跳过该客户"""
        analyzer = VicPersonaAnalyzer()
        mock_personas = [
            {"buyer_nick": "vic1"},
            {"buyer_nick": "vic2", "key_interests": ["奢侈品消费"]},
        ]
        result = analyzer.aggregate_interests(mock_personas)
        assert len(result) == 1
        assert result[0]["keyword"] == "奢侈品消费"
        assert result[0]["percentage"] == 50.0


class TestAggregatePainPoints:
    """VIC pain_points 聚合测试"""

    def test_aggregate_pain_points(self):
        """测试从多个 VIC 客户聚合 pain_points"""
        analyzer = VicPersonaAnalyzer()
        mock_personas = [
            {"buyer_nick": "vic1", "pain_points": ["尺码选择困难"]},
            {"buyer_nick": "vic2", "pain_points": ["尺码选择困难", "物流时效期望高"]},
        ]
        result = analyzer.aggregate_pain_points(mock_personas)
        assert result[0]["keyword"] == "尺码选择困难"
        assert result[0]["count"] == 2
        assert result[0]["percentage"] == 100.0

    def test_aggregate_pain_points_empty(self):
        """空列表应返回空结果"""
        analyzer = VicPersonaAnalyzer()
        result = analyzer.aggregate_pain_points([])
        assert result == []


class TestExtractMotivations:
    """购买动机模式提取测试"""

    def test_extract_motivations(self):
        """测试从 recommended_action 提取购买动机"""
        analyzer = VicPersonaAnalyzer()
        mock_personas = [
            {"buyer_nick": "vic1", "recommended_action": "推荐新品限量版烟斗"},
            {"buyer_nick": "vic2", "recommended_action": "老客回购优惠活动"},
        ]
        result = analyzer.extract_motivations(mock_personas)
        assert len(result) >= 1
        pattern_names = [r["pattern"] for r in result]
        assert "新品尝鲜者" in pattern_names
        assert "复购老客户" in pattern_names

    def test_extract_motivations_empty(self):
        """无 recommended_action 时应返回空结果"""
        analyzer = VicPersonaAnalyzer()
        mock_personas = [
            {"buyer_nick": "vic1"},
            {"buyer_nick": "vic2", "recommended_action": ""},
        ]
        result = analyzer.extract_motivations(mock_personas)
        assert result == []
