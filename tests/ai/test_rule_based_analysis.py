"""Tests for the rule-based sentiment+intent fallback (keyword_matcher).

These assert alignment with the AI prompt golden standard
(minimax_client.py:308 / deepseek_client.py:894):
  - refund / return / polite replies are NEUTRAL (not negative)
  - only strong negative / complaint words produce Negative
  - Logistics / Usage Guide intents are counted (previously hardcoded to 0)
  - jieba whole-token matching prevents single-char mismatches
"""
import keyword_matcher as km


# ---------------------------------------------------------------------------
# Sentiment: neutral-default model
# ---------------------------------------------------------------------------
class TestSentimentNeutralDefault:
    def test_refund_only_is_neutral(self):
        assert km.analyze_sentiment(['我要退款退货换货'])['sentiment_label'] == 'Neutral'

    def test_return_only_is_neutral(self):
        assert km.analyze_sentiment(['收到货了不合适帮我退货'])['sentiment_label'] == 'Neutral'

    def test_polite_replies_are_neutral(self):
        assert km.analyze_sentiment(['好的收到可以嗯'])['sentiment_label'] == 'Neutral'

    def test_empty_is_neutral(self):
        r = km.analyze_sentiment([])
        assert r['sentiment_label'] == 'Neutral'
        assert r['sentiment_score'] == 0.5

    def test_refund_with_dissatisfaction_is_negative(self):
        r = km.analyze_sentiment(['质量太差了，我要退款'])
        assert r['sentiment_label'] == 'Negative'

    def test_complaint_word_is_negative_and_heaviest(self):
        r = km.analyze_sentiment(['我要投诉给差评举报'])
        assert r['sentiment_label'] == 'Negative'
        assert r['sentiment_score'] == 0.25

    def test_strong_negative_alone_is_negative(self):
        r = km.analyze_sentiment(['这衣服质量太差了垃圾'])
        assert r['sentiment_label'] == 'Negative'
        assert r['sentiment_score'] == 0.3

    def test_strong_positive_is_positive(self):
        r = km.analyze_sentiment(['很满意会回购推荐给朋友'])
        assert r['sentiment_label'] == 'Positive'
        assert r['sentiment_score'] == 0.7

    def test_single_hao_in_buhao_is_negative_not_positive(self):
        # jieba must bind "不好" as a token; a lone "好" must NOT false-positive
        r = km.analyze_sentiment(['这东西不好用'])
        assert r['sentiment_label'] == 'Negative'

    def test_single_thanks_is_neutral(self):
        # A bare "谢谢" is polite, not a strong positive signal
        assert km.analyze_sentiment(['谢谢'])['sentiment_label'] == 'Neutral'


# ---------------------------------------------------------------------------
# Intent: 5-category classification
# ---------------------------------------------------------------------------
class TestIntentClassification:
    def test_logistics_is_counted(self):
        c = km.classify_intent_counts(['什么时候发货', '快递到哪了'])
        assert c['Logistics'] > 0

    def test_usage_guide_is_counted(self):
        c = km.classify_intent_counts(['这个皮具怎么保养清洗'])
        assert c['Usage Guide'] > 0

    def test_refund_is_post_sale_not_complaint(self):
        c = km.classify_intent_counts(['我要退款退货'])
        assert c['Post-sale Support'] > 0
        assert c['Complaint'] == 0

    def test_complaint_count_strong(self):
        assert km.complaint_count(['我要投诉给差评']) == 1

    def test_complaint_count_dissatisfaction(self):
        assert km.complaint_count(['质量太差了垃圾产品']) == 1

    def test_functional_request_without_dissatisfaction_not_complaint(self):
        assert km.complaint_count(['帮我催一下发货']) == 0

    def test_all_five_intent_keys_present(self):
        c = km.classify_intent_counts([])
        assert set(c.keys()) == {
            'Pre-sale Inquiry', 'Post-sale Support', 'Logistics',
            'Usage Guide', 'Complaint',
        }


# ---------------------------------------------------------------------------
# Full rule-based result shape
# ---------------------------------------------------------------------------
class TestFullRuleBased:
    _EXPECTED_KEYS = {
        'buyer_nick', 'sentiment_score', 'sentiment_label', 'intent_distribution',
        'dominant_intent', 'pre_sale_score', 'post_sale_score', 'pre_sale_keywords',
        'post_sale_keywords', 'complaint_count', 'sentiment_method', 'analyzed_at',
    }

    def test_returns_full_shape(self):
        r = km.analyze_rule_based('buyer1', ['什么时候发货', '很满意'])
        assert set(r.keys()) == self._EXPECTED_KEYS
        assert r['buyer_nick'] == 'buyer1'
        assert r['sentiment_method'] == 'rule_based'

    def test_refund_buyer_is_neutral_not_negative(self):
        # The headline regression: a refund-only customer must NOT be Negative
        r = km.analyze_rule_based('b', ['我要退款退货'])
        assert r['sentiment_label'] == 'Neutral'
        assert r['complaint_count'] == 0
