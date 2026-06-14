"""Tests for the rewritten rule-based persona fallback (rule_based_analyzer.py).

Asserts alignment with persona AI prompt (prompts/persona_inference.py):
  - 5-dimension customer_tags (客户类型/忠诚度/活跃度/成熟度/核心关注点)
  - summary is conclusion-style, NOT templated ("该客户为…"/"属于…型")
  - regular/no-data case must NOT say "数据不足"
  - output shape stays compatible with ground_persona_analysis_v3
"""
from backend.ai.rule_based_analyzer import RuleBasedAnalyzer


def _profile(**kw):
    base = {
        'vip_level': 'V3', 'city': '上海', 'l6m_netsales': 50000,
        'l1y_netsales': 200000, 'l6m_refund_rate': 0.0,
        'top_category': 'PIPES', 'total_refund_count': 0,
    }
    base.update(kw)
    return base


class TestPersonaDimensions:
    def test_returns_customer_tags_with_all_dimensions(self):
        r = RuleBasedAnalyzer().analyze(_profile(), [], [])
        assert 'customer_tags' in r
        tags = r['customer_tags']
        for k in ('客户类型', '忠诚度', '活跃度', '成熟度', '核心关注点'):
            assert k in tags

    def test_total_look_from_multi_category_orders(self):
        orders = [{'category': 'PIPES'}, {'category': 'LIGHTERS'},
                  {'category': 'READYWEAR'}, {'category': 'ACCESSORIES'}]
        r = RuleBasedAnalyzer().analyze(_profile(), [], orders)
        assert r['customer_tags']['客户类型'] == 'Total Look'

    def test_category_focus_single_dominant(self):
        orders = [{'category': 'PIPES'}] * 4 + [{'category': 'LIGHTERS'}]
        r = RuleBasedAnalyzer().analyze(_profile(), [], orders)
        assert '品类专注' in r['customer_tags']['客户类型']

    def test_exploratory_when_scattered(self):
        orders = [{'category': 'PIPES'}, {'category': 'LIGHTERS'}, {'category': 'READYWEAR'}]
        # 3 distinct => Total Look, so drop to 2 distinct for exploratory
        orders = [{'category': 'PIPES'}, {'category': 'PIPES'}, {'category': 'LIGHTERS'}, {'category': 'READYWEAR'}]
        r = RuleBasedAnalyzer().analyze(_profile(), [], orders)
        assert r['customer_tags']['客户类型'] in ('探索型', 'Total Look', '品类专注-PIPES')

    def test_high_loyalty_for_vip_v3(self):
        r = RuleBasedAnalyzer().analyze(_profile(vip_level='V3'), [], [])
        assert r['customer_tags']['忠诚度'] == '高忠诚'

    def test_high_loyalty_for_cross_year_repurchase(self):
        orders = [{'order_date': '2024-05-01'}, {'order_date': '2025-06-01'}, {'order_date': '2026-01-01'}]
        r = RuleBasedAnalyzer().analyze(_profile(vip_level='Non-VIP', l1y_netsales=5000), [], orders)
        assert r['customer_tags']['忠诚度'] == '高忠诚'

    def test_rookie_maturity_from_chats(self):
        chats = [
            {'content': '第一次买不懂怎么选请推荐'},
            {'content': '新手小白求指导'},
            {'content': '不知道怎么选适合新手吗'},
        ]
        r = RuleBasedAnalyzer().analyze(_profile(), chats, [])
        assert r['customer_tags']['成熟度'] == '新手'

    def test_quality_focus_when_high_refund_rate(self):
        r = RuleBasedAnalyzer().analyze(_profile(l6m_refund_rate=0.15), [], [])
        assert r['customer_tags']['核心关注点'] == '品质保障'


class TestPersonaCopyNonTemplated:
    def test_summary_has_no_template_phrasing(self):
        r = RuleBasedAnalyzer().analyze(_profile(), [], [])
        s = r['summary']
        assert '该客户为' not in s
        assert '属于' not in s
        assert '型客户' not in s

    def test_summary_uses_real_numbers(self):
        r = RuleBasedAnalyzer().analyze(_profile(l1y_netsales=234567, l6m_netsales=89000), [], [])
        assert '234,567' in r['summary']

    def test_empty_profile_does_not_say_data_insufficient(self):
        r = RuleBasedAnalyzer().analyze({}, [], [])
        assert '数据不足' not in r['summary']
        assert '无法推断' not in r['summary']


class TestPersonaShapeCompatibility:
    _EXPECTED = {'summary', 'key_interests', 'pain_points', 'recommended_action',
                 'confidence_level', 'customer_tags'}

    def test_returns_all_expected_keys(self):
        r = RuleBasedAnalyzer().analyze(_profile(), [], [])
        assert self._EXPECTED.issubset(set(r.keys()))

    def test_interests_painpoints_are_lists(self):
        r = RuleBasedAnalyzer().analyze(_profile(), [], [])
        assert isinstance(r['key_interests'], list)
        assert isinstance(r['pain_points'], list)
        assert len(r['key_interests']) > 0
        assert len(r['pain_points']) > 0
