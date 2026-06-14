"""
Keyword matcher with jieba tokenization for rule-based fallback analysis.

Centralizes word lists (single source of truth) and whole-token matching to align
the rule-based fallback with the AI prompt standards:

- sentiment: neutral is the DEFAULT baseline; only strong signals move the score.
  Functional / polite words (refund, return, "thanks", "ok") are neutral and do NOT
  participate in scoring — previously they were wrongly counted as negative.
- intent: 5-category per-message classification (Pre-sale / Post-sale / Logistics /
  Usage Guide / Complaint).

Matching uses jieba tokenization with contiguous-token concatenation, so:
  * single chars never mismatch (e.g. "好" no longer matches inside "不好")
  * words jieba splits still match (e.g. "质量差" == "质量"+"差")

Word lists below mirror the sentiment/intent definitions in
``minimax_client.py`` / ``deepseek_client.py`` prompts (the golden standard).
"""
from __future__ import annotations

from typing import Dict, List

import jieba

# ---------------------------------------------------------------------------
# jieba initialization (once, lazy)
# ---------------------------------------------------------------------------
_jieba_ready = False


def _ensure_jieba() -> None:
    global _jieba_ready
    if not _jieba_ready:
        jieba.initialize()
        _jieba_ready = True


# ---------------------------------------------------------------------------
# SENTIMENT word lists (aligned to AI prompt, minimax_client.py:308 / deepseek:894)
# Only "emotional evaluation" and "complaint action" words participate in scoring.
# ---------------------------------------------------------------------------
STRONG_NEGATIVE = [
    '太差', '很差', '质量差', '质量太差', '质量不好', '做工差', '差劲',
    '垃圾', '骗子', '假货', '欺骗', '失望', '不满', '不满意',
    '态度差', '服务差', '不好用', '太慢',
    # colloquial negative expressions surfaced by regression on real chats
    '一塌糊涂', '不怎样', '瞎扯', '太恶心', '忍无可忍', '骚扰', '粘毛',
]

COMPLAINT_ACTION = [
    '投诉', '差评', '给差评', '举报',
    '315', '消费者协会', '工商', '找经理',
]

STRONG_POSITIVE = [
    '满意', '很满意', '非常满意', '感谢', '非常感谢', '谢谢支持',
    '喜欢', '很喜欢', '不错', '很好', '非常好', '质量好', '好评', '给好评',
    '回购', '再买', '推荐给', '下次还来', '推荐朋友',
]

# Functional / polite words — NEUTRAL, do NOT participate in sentiment scoring.
# Documented here for clarity and single-source-of-truth; intentionally unscored.
FUNCTIONAL_NEUTRAL = [
    '退款', '退货', '换货', '收到', '好的', '可以', '嗯',
    '问题', '发货', '物流', '快递', '多少钱', '有没有货',
    '收到货', '催促',
]


# ---------------------------------------------------------------------------
# INTENT word lists (migrated from batch_analyzer._classify_intents_by_keywords:825-853)
# ---------------------------------------------------------------------------
INTENT_PRE_SALE = [
    '价格', '多少钱', '有货', '现货', '库存', '尺寸', '尺码', '颜色',
    '款式', '推荐', '新款', '上市', '还有吗', '链接', '双面', '材质',
    '面料', '羊绒', '骆驼绒', '标识', '徽标', 'ad标', '长尾标',
    '适合', '合身', '多大', '腰围', '胸围', '可以买吗', '怎么买',
]

INTENT_POST_SALE = [
    '退货', '退了', '退款', '退一下', '换货', '换成', '调换', '维修',
    '保修', '发票', '收到', '收到了', '售后', '售后服务', '裁袖',
    '裁一下', '修改', '改袖', '改裤脚', '签收', '寄到', '瑕疵',
    '划痕', '黑点', '小瑕疵', '包边', '带头', '不舒服', '不合适',
    '不想要', '发错', '少发', '漏发', '色差', '掉色', '褪色',
    '破损', '坏了', '有问题', '质量问题', '做工', '污渍',
]

INTENT_LOGISTICS = [
    '物流', '快递', '发货', '发出', '发了吗', '运单', '单号',
    '顺丰', '什么时候到', '配送', '寄出', '寄到', '签收', '地址',
]

INTENT_USAGE = [
    '怎么用', '如何使用', '保养', '清洗', '维护', '说明', '教程',
    '安装', '使用方法', '护理',
]

INTENT_STRONG_COMPLAINT = [
    '投诉', '差评', '举报', '315', '消费者协会', '工商', '找经理',
]

INTENT_DISSATISFACTION = [
    '太差', '质量差', '很差', '垃圾', '骗子', '骗人', '假的', '假货', '欺骗',
    '失望', '不满', '不满意', '太慢', '态度差', '服务差', '差的', '不好用',
    '质量太差', '质量不好', '做工差', '掉色', '褪色', '破损', '坏了', '有问题',
    '差劲', '太差了', '质量太差了', '差评', '给差评',
]

# Functional request words — a refund/return alone (without dissatisfaction) is NOT
# a complaint. Used for documentation / potential future disambiguation.
INTENT_FUNCTIONAL = ['退款', '退货', '换货', '催促', '发货', '收到货', '物流']


# ---------------------------------------------------------------------------
# Matching primitives
# ---------------------------------------------------------------------------
def tokenize(text: str) -> List[str]:
    """Jieba-tokenize text into non-empty tokens."""
    _ensure_jieba()
    return [t for t in jieba.lcut(text or '') if t and t.strip()]


def _term_in_tokens(term: str, tokens: List[str]) -> bool:
    """True if ``term`` equals a single token or a contiguous run of tokens.

    This is the crux of jieba-based matching: whole-token precision (a lone "好"
    only matches if jieba actually emits it as a token, so it won't fire inside
    "不好") while still matching words jieba over-splits ("质量差" == "质量"+"差").
    """
    if not term or not tokens:
        return False
    if term in tokens:
        return True
    n = len(tokens)
    tlen = len(term)
    for i in range(n):
        if len(tokens[i]) > tlen:
            continue
        acc = tokens[i]
        for j in range(i + 1, n):
            acc += tokens[j]
            if len(acc) > tlen:
                break
            if acc == term:
                return True
    return False


def match_terms(text: str, terms: List[str]) -> int:
    """Count how many ``terms`` appear in ``text`` (whole-token / contiguous match).

    Returns the number of distinct terms hit (kind count, not frequency).
    """
    if not text or not terms:
        return 0
    tokens = [t.lower() for t in tokenize(text)]
    count = 0
    for term in terms:
        if _term_in_tokens(term.lower(), tokens):
            count += 1
    return count


def any_term(text: str, terms: List[str]) -> bool:
    """True if any term appears in text (whole-token / contiguous match)."""
    if not text or not terms:
        return False
    tokens = [t.lower() for t in tokenize(text)]
    return any(_term_in_tokens(t.lower(), tokens) for t in terms)


# ---------------------------------------------------------------------------
# Intent classification (per-message, message-count per category)
# ---------------------------------------------------------------------------
INTENT_KEYS = ["Pre-sale Inquiry", "Post-sale Support", "Logistics", "Usage Guide", "Complaint"]


def classify_intent_counts(messages: List[str]) -> Dict[str, int]:
    """Per-message 5-category intent classification.

    Each message can contribute to multiple categories (mirrors the original
    ``_classify_intents_by_keywords`` behavior). Complaint is special: it follows
    the three-tier rule (strong-complaint / dissatisfaction word => 1 for the whole
    conversation; functional-only request => 0), so it is 0/1, not a message count.
    Logistics / Usage Guide are now live (previously hardcoded to 0).
    """
    counts = {k: 0 for k in INTENT_KEYS}
    for msg in messages or []:
        text = (msg or '').lower()
        if not text.strip():
            continue
        tokens = [t.lower() for t in tokenize(msg)]
        if any(_term_in_tokens(t.lower(), tokens) for t in INTENT_PRE_SALE):
            counts["Pre-sale Inquiry"] += 1
        if any(_term_in_tokens(t.lower(), tokens) for t in INTENT_POST_SALE):
            counts["Post-sale Support"] += 1
        if any(_term_in_tokens(t.lower(), tokens) for t in INTENT_LOGISTICS):
            counts["Logistics"] += 1
        if any(_term_in_tokens(t.lower(), tokens) for t in INTENT_USAGE):
            counts["Usage Guide"] += 1
    counts["Complaint"] = complaint_count(messages)
    return counts


def complaint_count(messages: List[str]) -> int:
    """Three-tier complaint logic over the whole conversation.

    Returns 1 if any strong-complaint OR dissatisfaction word appears, else 0.
    A pure functional request (refund/return) without dissatisfaction does NOT count
    as a complaint — aligned with the AI prompt and the original :927-940 logic.
    """
    all_text = ' '.join((m or '') for m in (messages or []))
    if not all_text.strip():
        return 0
    if any_term(all_text, INTENT_STRONG_COMPLAINT) or any_term(all_text, INTENT_DISSATISFACTION):
        return 1
    return 0


# ---------------------------------------------------------------------------
# Rule-based sentiment + intent analysis (pure logic, only depends on jieba)
# ---------------------------------------------------------------------------
def _intent_scores(intent_dist: Dict[str, int]) -> Dict[str, int]:
    """Pre-sale / post-sale scores from intent distribution (0-100).

    Mirrors ``TagCalculator.calculate_intent_scores`` (tag_calculator.py:609) but
    inlined here so this module stays dependency-free and unit-testable in isolation.
    """
    total = sum(intent_dist.values()) or 1
    pre = min(100, int(intent_dist.get("Pre-sale Inquiry", 0) / total * 100))
    post_count = (
        intent_dist.get("Post-sale Support", 0)
        + intent_dist.get("Complaint", 0)
        + intent_dist.get("Usage Guide", 0)
    )
    post = min(100, int(post_count / total * 100))
    return {"pre_sale_score": pre, "post_sale_score": post}


def analyze_sentiment(messages: List[str]) -> Dict[str, Any]:
    """Neutral-default sentiment scoring.

    Default is Neutral (0.5). Only strong signals move the score:
      - complaint action  -> 0.25 (Negative, heaviest)
      - strong negative   -> 0.30 (Negative)
      - neg + pos         -> 0.40 (Negative, negative wins)
      - strong positive   -> 0.70 (Positive)
    Functional / polite words never participate. Boundaries follow the AI prompt:
    score < 0.4 Negative, > 0.6 Positive, else Neutral (closed interval).
    """
    all_text = ' '.join((m or '') for m in (messages or []))
    complaint_hit = any_term(all_text, COMPLAINT_ACTION)
    neg_hit = any_term(all_text, STRONG_NEGATIVE)
    pos_hit = any_term(all_text, STRONG_POSITIVE)

    if complaint_hit:
        score = 0.25
    elif neg_hit and not pos_hit:
        score = 0.30
    elif neg_hit and pos_hit:
        score = 0.40
    elif pos_hit and not neg_hit:
        score = 0.70
    else:
        score = 0.50

    if score < 0.4:
        label = 'Negative'
    elif score > 0.6:
        label = 'Positive'
    else:
        label = 'Neutral'

    return {"sentiment_score": round(score, 2), "sentiment_label": label}


def analyze_rule_based(buyer_nick: str, messages: List[str]) -> Dict[str, Any]:
    """Full rule-based sentiment + intent analysis (the L3 fallback).

    Returns the same dict shape as ``BatchAnalyzer._rule_based_analysis`` so it is
    a drop-in replacement. Pure logic: only depends on jieba (no project imports),
    which keeps it unit-testable and regression-runnable without the full backend
    dependency stack.
    """
    from datetime import datetime

    sentiment = analyze_sentiment(messages)
    intent_dist = classify_intent_counts(messages)
    comp = complaint_count(messages)

    mx = max(intent_dist.values()) if intent_dist else 0
    dominant = max(INTENT_KEYS, key=lambda k: intent_dist[k]) if mx > 0 else "Unknown"
    scores = _intent_scores(intent_dist)

    return {
        "buyer_nick": buyer_nick,
        "sentiment_score": sentiment["sentiment_score"],
        "sentiment_label": sentiment["sentiment_label"],
        "intent_distribution": intent_dist,
        "dominant_intent": dominant,
        "pre_sale_score": scores["pre_sale_score"],
        "post_sale_score": scores["post_sale_score"],
        "pre_sale_keywords": [],
        "post_sale_keywords": [],
        "complaint_count": comp,
        "sentiment_method": "rule_based",
        "analyzed_at": datetime.now(),
    }
