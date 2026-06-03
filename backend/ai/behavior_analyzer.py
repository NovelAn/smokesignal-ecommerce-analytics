"""
Behavior Analyzer - 订单行为结构化分析
"""
from collections import Counter
from typing import Dict, List, Any
from datetime import datetime
from backend.ai.data_extractor import detect_rookie_signal, detect_expert_signal


def structure_order_behavior(profile: Dict, orders: List[Dict]) -> Dict[str, Any]:
    """
    将订单数据转换为结构化行为特征

    Args:
        profile: 客户档案数据
        orders: 订单列表

    Returns:
        {
            "购买特征": Dict,
            "售后行为": Dict,
            "沟通特征": Dict,
            "价值特征": Dict
        }
    """
    return {
        "购买特征": analyze_purchase_features(profile, orders),
        "售后行为": analyze_after_sales_behavior(profile, orders),
        "沟通特征": analyze_communication_pattern(profile),
        "价值特征": analyze_value_metrics(profile)
    }


def build_order_facts(profile: Dict, orders: List[Dict], top_n: int = 8) -> Dict[str, Any]:
    """Build a compact but authoritative fact pack for persona prompts."""
    total_orders = len(orders or [])
    total_payment = 0.0
    dated_orders = []
    category_counts: Counter[str] = Counter()
    year_counts: Counter[str] = Counter()
    month_counts: Counter[str] = Counter()

    for order in orders or []:
        payment = float(order.get("payment", 0) or 0)
        total_payment += payment

        category = normalize_category(order.get("category"))
        if category:
            category_counts[category] += 1

        paid_at = extract_order_datetime(order)
        if paid_at:
            dated_orders.append((paid_at, order))
            year_counts[str(paid_at.year)] += 1
            month_counts[f"{paid_at.year}-{paid_at.month:02d}"] += 1

    dated_orders.sort(key=lambda item: item[0], reverse=True)

    top_categories = [
        {
            "category": category,
            "order_lines": count,
            "percentage": round(count / total_orders * 100, 1) if total_orders else 0.0,
        }
        for category, count in category_counts.most_common()
    ]
    year_breakdown = [
        {"year": year, "order_lines": count, "percentage": round(count / total_orders * 100, 1)}
        for year, count in year_counts.most_common()
    ]
    month_breakdown = [
        {"month": month, "order_lines": count, "percentage": round(count / total_orders * 100, 1)}
        for month, count in month_counts.most_common(6)
    ]

    recent_orders = []
    for paid_at, order in dated_orders[:top_n]:
        recent_orders.append({
            "pay_time": paid_at.strftime("%Y-%m-%d"),
            "commodity_name": order.get("commodity_name", ""),
            "category": normalize_category(order.get("category")),
            "payment": round(float(order.get("payment", 0) or 0), 2),
        })

    authoritative_total_orders = int(float(profile.get("total_orders", 0) or 0)) or total_orders
    authoritative_total_payment = total_payment or float(profile.get("historical_net_sales", 0) or 0)
    authoritative_net_sales = float(profile.get("historical_net_sales", 0) or 0)
    avg_order_value = (
        authoritative_total_payment / authoritative_total_orders
        if authoritative_total_orders else 0.0
    )
    discount_ratio = float(profile.get("discount_ratio", 0) or 0)
    discount_sensitivity = profile.get("discount_sensitivity", "未知")

    peak_months = [item["month"] for item in month_breakdown[:3]]
    peak_years = [item["year"] for item in year_breakdown[:3]]

    facts = {
        "total_orders": authoritative_total_orders,
        "order_lines_in_prompt": total_orders,
        "total_payment": round(authoritative_total_payment, 2),
        "total_net_sales": round(authoritative_net_sales, 2),
        "avg_order_value": round(avg_order_value, 2),
        "discount_ratio": discount_ratio,
        "discount_sensitivity": discount_sensitivity,
        "top_categories": top_categories[:8],
        "year_breakdown": year_breakdown,
        "month_breakdown": month_breakdown,
        "peak_years": peak_years,
        "peak_months": peak_months,
        "recent_orders": recent_orders,
        "category_groups": calculate_category_distribution(orders).get("category_groups", []),
        "stage_summary": calculate_category_distribution(orders).get("stage_summary", ""),
        "order_span_days": _calculate_order_span_days(dated_orders),
        "spend_seasonality": _build_spend_seasonality(year_breakdown, month_breakdown),
    }
    facts.update(build_persona_order_signals(profile, orders, facts))
    return facts


def ground_persona_analysis(result: Dict[str, Any], profile: Dict, orders: List[Dict]) -> Dict[str, Any]:
    """Overwrite fragile model claims with deterministic buyer facts."""
    facts = build_order_facts(profile, orders, top_n=12)
    if not facts.get("total_orders"):
        return result

    grounded = dict(result or {})
    total_orders = facts["total_orders"]
    aov = facts["avg_order_value"]
    discount_ratio = float(facts.get("discount_ratio") or 0)
    discount_sensitivity = facts.get("discount_sensitivity") or "未知"
    top_category = facts.get("top_categories", [{}])[0] if facts.get("top_categories") else {}
    top_group = facts.get("category_groups", [{}])[0] if facts.get("category_groups") else {}
    promo = _calculate_promo_window(facts)

    category_text = _format_category_trait(top_category, top_group)
    discount_text = _format_discount_trait(discount_ratio, discount_sensitivity, promo)
    promo_text = _format_promo_trait(promo)

    grounded["summary"] = (
        f"历史{total_orders}单，AOV约¥{aov:,.0f}；{promo_text}。"
        f"{category_text}。{discount_text}。"
    )

    interests = [
        promo["interest"],
        category_text,
        f"AOV约¥{aov:,.0f}，折扣占比{discount_ratio:.0%}，折扣敏感度为{discount_sensitivity}",
    ]
    grounded["key_interests"] = _dedupe_nonempty(interests + grounded.get("key_interests", []), limit=4)

    pain_points = [
        promo["risk"],
        _category_expansion_risk(top_category, top_group),
    ]
    grounded["pain_points"] = _dedupe_nonempty(pain_points + grounded.get("pain_points", []), limit=3)

    grounded["recommended_action"] = (
        "在618、双11/双12、季末特惠前主动触达；主推其高频上装/Polo相关款，"
        "并用皮带、配饰等低频已购品类做搭配扩展。"
    )
    grounded["fact_guard_applied"] = True
    return grounded


def ground_persona_analysis_v2(result: Dict[str, Any], profile: Dict, orders: List[Dict]) -> Dict[str, Any]:
    """Correct impossible numeric claims without overwriting model insight."""
    facts = build_order_facts(profile, orders, top_n=12)
    if not facts.get("total_orders"):
        return result

    grounded = dict(result or {})
    aov = float(facts.get("avg_order_value") or 0)
    discount_ratio = float(facts.get("discount_ratio") or 0)
    discount_sensitivity = facts.get("discount_sensitivity") or "未知"
    top_category = facts.get("top_categories", [{}])[0] if facts.get("top_categories") else {}
    top_group = facts.get("category_groups", [{}])[0] if facts.get("category_groups") else {}
    promo = _calculate_promo_window(facts)

    category_text = _format_category_trait(top_category, top_group)
    promo_text = _format_promo_trait(promo)
    discount_text = _format_discount_trait(discount_ratio, discount_sensitivity, promo)

    summary = str(grounded.get("summary") or "").strip()
    if not summary or _looks_numeric_failure(summary, facts):
        grounded["summary"] = (
            f"{promo_text}；{category_text}；{discount_text}。"
            "需结合聊天记录继续提炼客户关注点、顾虑和触达话术。"
        )
    else:
        grounded["summary"] = _remove_contradictory_claims(summary, facts)

    fact_interests = [
        promo["interest"],
        category_text,
        f"AOV约¥{aov:,.0f}，折扣占比{discount_ratio:.0%}，折扣敏感度为{discount_sensitivity}",
    ]
    grounded["key_interests"] = _dedupe_nonempty(grounded.get("key_interests", []) + fact_interests, limit=5)

    fact_pain_points = [
        promo["risk"],
        _category_expansion_risk(top_category, top_group),
    ]
    grounded["pain_points"] = _dedupe_nonempty(grounded.get("pain_points", []) + fact_pain_points, limit=4)

    if not str(grounded.get("recommended_action") or "").strip():
        grounded["recommended_action"] = (
            "结合聊天记录里的关注点制定话术；若聊天信息不足，优先围绕大促前上装/Polo新品、"
            "尺码搭配和低频配饰扩展做召回。"
        )

    grounded["fact_evidence"] = {
        "total_orders": facts.get("total_orders"),
        "avg_order_value": round(aov, 2),
        "discount_ratio": discount_ratio,
        "discount_sensitivity": discount_sensitivity,
        "promo_window_share": round(float(promo.get("share", 0)), 4),
        "category_trait": category_text,
    }
    grounded["fact_guard_applied"] = True
    return grounded


def ground_persona_analysis_v3(result: Dict[str, Any], profile: Dict, orders: List[Dict]) -> Dict[str, Any]:
    """Preserve model insight while attaching clean authoritative fact evidence."""
    facts = build_order_facts(profile, orders, top_n=12)
    if not facts.get("total_orders"):
        return result

    grounded = dict(result or {})
    total_orders = int(facts.get("total_orders") or 0)
    aov = float(facts.get("avg_order_value") or 0)
    discount_ratio = float(facts.get("discount_ratio") or 0)
    discount_sensitivity = str(facts.get("discount_sensitivity") or "未知")
    promo_window = facts.get("promo_window") or {}
    promo_share = float(promo_window.get("share") or 0)
    promo_judgement = promo_window.get("judgement") or judge_purchase_timing(promo_share)
    top_categories = facts.get("top_categories") or []
    category_groups = facts.get("category_groups") or []

    category_trait = _clean_category_trait(top_categories, category_groups)
    discount_trait = judge_discount_mindset(discount_ratio, promo_share, discount_sensitivity)
    timing_trait = f"{promo_judgement}，大促/季末窗口贡献{promo_window.get('count', 0)}/{facts.get('order_lines_in_prompt', total_orders)}单（{promo_share:.0%}）"

    summary = str(grounded.get("summary") or "").strip()
    if not summary or _looks_numeric_failure(summary, facts):
        grounded["summary"] = (
            f"{category_trait}；{timing_trait}；{discount_trait}。"
            "聊天证据需要继续用于识别尺码、搭配、物流、退换货等具体顾虑。"
        )
    else:
        grounded["summary"] = _remove_contradictory_claims(summary, facts)

    trait_dimensions = grounded.get("trait_dimensions")
    if not isinstance(trait_dimensions, dict):
        trait_dimensions = {}
    trait_dimensions.setdefault("category_preference", category_trait)
    trait_dimensions.setdefault("discount_mindset", discount_trait)
    trait_dimensions.setdefault("price_sensitivity", discount_trait)
    trait_dimensions.setdefault("purchase_timing", timing_trait)
    trait_dimensions.setdefault("chat_concerns", "聊天证据不足")
    trait_dimensions.setdefault("communication_style", "需结合聊天记录继续判断")
    trait_dimensions.setdefault("pain_or_growth_opportunity", _clean_growth_opportunity(facts))
    grounded["trait_dimensions"] = trait_dimensions

    evidence_items = [
        timing_trait,
        category_trait,
        f"AOV约{aov:,.0f}，MD占比{discount_ratio:.0%}，折扣敏感度为{discount_sensitivity}",
    ]
    grounded["key_interests"] = _dedupe_nonempty(grounded.get("key_interests", []) + evidence_items, limit=5)
    grounded["pain_points"] = _dedupe_nonempty(
        grounded.get("pain_points", []) + [_clean_growth_opportunity(facts)],
        limit=4,
    )

    grounded["fact_evidence"] = {
        "total_orders": total_orders,
        "avg_order_value": round(aov, 2),
        "discount_ratio": discount_ratio,
        "discount_sensitivity": discount_sensitivity,
        "computed_md_ratio_from_orders": facts.get("computed_md_ratio_from_orders"),
        "fp_md_counts": facts.get("fp_md_counts"),
        "promo_window": promo_window,
        "top_categories": top_categories[:5],
        "category_groups": category_groups[:5],
        "refund_behavior": facts.get("refund_behavior"),
        "price_band": facts.get("price_band"),
    }
    grounded["fact_guard_applied"] = True
    return grounded


def _clean_category_trait(top_categories: List[Dict[str, Any]], category_groups: List[Dict[str, Any]]) -> str:
    top_group = category_groups[0] if category_groups else {}
    top_category = top_categories[0] if top_categories else {}
    group = top_group.get("group") or "未知大类"
    group_label = "男士上装/成衣" if group == "READYWEAR" else group
    group_count = int(top_group.get("order_lines", 0) or 0)
    group_pct = float(top_group.get("percentage", 0) or 0)
    category = top_category.get("category") or "未知品类"
    category_count = int(top_category.get("order_lines", 0) or 0)
    category_pct = float(top_category.get("percentage", 0) or 0)
    if group_count:
        return f"品类偏好集中在{group_label}（{group_count}单，占{group_pct:.1f}%），其中{category}最高频（{category_count}单，占{category_pct:.1f}%）"
    return f"最高频品类为{category}（{category_count}单，占{category_pct:.1f}%），但大类归因证据不足"


def _clean_growth_opportunity(facts: Dict[str, Any]) -> str:
    promo_share = float((facts.get("promo_window") or {}).get("share") or 0)
    category_groups = facts.get("category_groups") or []
    top_group = category_groups[0] if category_groups else {}
    if promo_share >= 0.5:
        return "非大促/季末窗口的主动转化可能偏弱，需要提前在活动节点前做召回和新品预热"
    if top_group.get("group") == "READYWEAR" and float(top_group.get("percentage", 0) or 0) >= 80:
        return "品类高度集中在男士上装/成衣，鞋包皮具等跨品类扩展仍需要搭配场景引导"
    return "需要结合聊天关注点进一步提升个性化推荐和复购触达"


def _looks_numeric_failure(summary: str, facts: Dict[str, Any]) -> bool:
    if not summary:
        return True
    discount_ratio = float(facts.get("discount_ratio") or 0)
    if discount_ratio > 0 and ("折扣占比0%" in summary or "MD占比0%" in summary or "对折扣完全无感" in summary):
        return True
    actual_aov = int(round(float(facts.get("avg_order_value") or 0)))
    if actual_aov > 0:
        import re
        for raw in re.findall(r"AOV(?:约|达)?[¥￥]?\s*([0-9,]+)", summary, flags=re.IGNORECASE):
            claimed = int(raw.replace(",", ""))
            if abs(claimed - actual_aov) > max(300, actual_aov * 0.12):
                return True
    return False


def build_persona_order_signals(profile: Dict, orders: List[Dict], base_facts: Dict[str, Any]) -> Dict[str, Any]:
    """Derive business-readable persona signals from raw order fields."""
    orders = orders or []
    total_lines = len(orders)
    fp_md_counts: Counter[str] = Counter()
    promo_counts: Counter[str] = Counter()
    category_group_counts: Counter[str] = Counter()
    same_day_counts: Counter[str] = Counter()
    payments = []
    total_refund = 0.0
    total_quantity = 0
    recent_product_names = []

    for order in orders:
        payment = _safe_order_float(order, "payment", "成交总金额")
        refund = _safe_order_float(order, "refund_amount", "退款金额")
        quantity = int(_safe_order_float(order, "quantity", "件数") or 0)
        if payment > 0:
            payments.append(payment)
        total_refund += refund
        total_quantity += quantity

        fp_md = normalize_fp_md(_order_value(order, "fp_md", "FP_MD"))
        if fp_md:
            fp_md_counts[fp_md] += 1

        category = normalize_category(order.get("category"))
        if category:
            category_group_counts[classify_category_group(category)] += 1

        paid_at = extract_order_datetime(order)
        if paid_at:
            same_day_counts[paid_at.strftime("%Y-%m-%d")] += 1
            promo_label = classify_promo_window(paid_at)
            if promo_label:
                promo_counts[promo_label] += 1

        name = str(_order_value(order, "commodity_name", "商品名称") or "").strip()
        if name:
            recent_product_names.append(name[:80])

    prompt_lines = int(base_facts.get("order_lines_in_prompt") or total_lines or 0)
    md_ratio_from_orders = fp_md_counts.get("MD", 0) / prompt_lines if prompt_lines else 0.0
    discount_ratio = float(base_facts.get("discount_ratio") or 0) or md_ratio_from_orders
    promo_count = sum(promo_counts.values())
    promo_share = promo_count / prompt_lines if prompt_lines else 0.0
    payments = sorted(payments)
    total_payment = float(base_facts.get("total_payment") or sum(payments) or 0)

    category_groups = [
        {
            "group": group,
            "order_lines": count,
            "percentage": round(count / prompt_lines * 100, 1) if prompt_lines else 0.0,
        }
        for group, count in category_group_counts.most_common()
    ]

    return {
        "fp_md_counts": dict(fp_md_counts),
        "computed_md_ratio_from_orders": round(md_ratio_from_orders, 4),
        "discount_mindset": judge_discount_mindset(
            discount_ratio,
            promo_share,
            str(base_facts.get("discount_sensitivity") or profile.get("discount_sensitivity") or "未知"),
        ),
        "promo_window": {
            "count": promo_count,
            "share": round(promo_share, 4),
            "breakdown": [
                {"window": window, "order_lines": count}
                for window, count in promo_counts.most_common()
            ],
            "judgement": judge_purchase_timing(promo_share),
        },
        "category_groups": category_groups or base_facts.get("category_groups", []),
        "same_day_multi_order": [
            {"date": day, "order_lines": count}
            for day, count in same_day_counts.most_common()
            if count >= 2
        ][:5],
        "price_band": {
            "min_payment": round(payments[0], 2) if payments else 0.0,
            "max_payment": round(payments[-1], 2) if payments else 0.0,
            "median_payment": round(payments[len(payments) // 2], 2) if payments else 0.0,
            "avg_line_payment": round(sum(payments) / len(payments), 2) if payments else 0.0,
        },
        "refund_behavior": {
            "refund_amount": round(total_refund, 2),
            "refund_rate_by_payment": round(total_refund / total_payment, 4) if total_payment else 0.0,
            "refund_order_lines": sum(1 for order in orders if _safe_order_float(order, "refund_amount", "退款金额") > 0),
        },
        "total_quantity": total_quantity,
        "recent_product_names": recent_product_names[:8],
    }


def _order_value(order: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in order and order.get(key) is not None:
            return order.get(key)
    return None


def _safe_order_float(order: Dict[str, Any], *keys: str) -> float:
    value = _order_value(order, *keys)
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def normalize_fp_md(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"MD", "FP"}:
        return text
    return ""


def classify_promo_window(paid_at: datetime) -> str:
    month = paid_at.month
    if month in {5, 6}:
        return "618/season-end"
    if month in {10, 11, 12}:
        return "Double11/Double12/winter-promo"
    return ""


def judge_purchase_timing(promo_share: float) -> str:
    if promo_share >= 0.7:
        return "固定在平台大促/季末节点集中购买"
    if promo_share >= 0.4:
        return "有一定活动窗口倾向"
    return "无明显集中度，购买较分散"


def judge_discount_mindset(discount_ratio: float, promo_share: float, discount_sensitivity: str) -> str:
    if discount_ratio >= 0.7:
        return "高MD占比，明确大促折扣心智，价格敏感度高"
    if discount_ratio >= 0.4:
        return "MD占比中高，叠加活动窗口时可判断为价格敏感"
    if promo_share >= 0.5:
        return f"MD占比{discount_ratio:.0%}、{discount_sensitivity}，但购买高度集中在大促/季末窗口，属于活动节点型决策，不应写成折扣无感"
    return f"MD占比{discount_ratio:.0%}、{discount_sensitivity}，暂不宜判断为强折扣驱动"


def _remove_contradictory_claims(summary: str, facts: Dict[str, Any]) -> str:
    discount_ratio = float(facts.get("discount_ratio") or 0)
    if discount_ratio > 0:
        summary = summary.replace("对折扣完全无感", "不是纯低价驱动")
        summary = summary.replace("折扣占比0%", f"折扣占比{discount_ratio:.0%}")
        summary = summary.replace("MD占比0%", f"MD占比{discount_ratio:.0%}")
    return summary


def _calculate_promo_window(facts: Dict[str, Any]) -> Dict[str, Any]:
    promo_months = {5, 6, 10, 11, 12}
    total = int(facts.get("order_lines_in_prompt") or facts.get("total_orders") or 0)
    promo_count = 0
    month_labels = []
    for item in facts.get("month_breakdown", []):
        month = str(item.get("month", ""))
        try:
            month_num = int(month[-2:])
        except ValueError:
            continue
        if month_num in promo_months:
            count = int(item.get("order_lines", 0) or 0)
            promo_count += count
            month_labels.append(month)

    share = promo_count / total if total else 0
    month_text = "、".join(month_labels[:4]) if month_labels else "大促期"
    return {
        "count": promo_count,
        "share": share,
        "months": month_text,
        "interest": f"大促窗口购买集中：{month_text}贡献{promo_count}/{total}单（{share:.0%}）",
        "risk": "非大促窗口主动购买较少，日常正价触达转化可能偏弱" if share >= 0.5 else "购买节奏分散，需结合近期品类偏好触达",
    }


def _format_promo_trait(promo: Dict[str, Any]) -> str:
    if promo.get("share", 0) >= 0.5:
        return f"购买高峰明显集中在{promo['months']}等平台大促/季末节点（{promo['count']}单，占{promo['share']:.0%}）"
    return f"购买月份相对分散，大促窗口贡献{promo['count']}单（占{promo['share']:.0%}）"


def _format_category_trait(top_category: Dict[str, Any], top_group: Dict[str, Any]) -> str:
    category = top_category.get("category", "未知品类")
    category_count = int(top_category.get("order_lines", 0) or 0)
    category_pct = float(top_category.get("percentage", 0) or 0)
    group = top_group.get("group", "")
    group_count = int(top_group.get("order_lines", 0) or 0)
    group_pct = float(top_group.get("percentage", 0) or 0)
    group_label = "男士上装/成衣" if group == "READYWEAR" else group or "多品类"
    if group_count and group != category:
        return f"品类偏好集中在{group_label}（{group_count}单，占{group_pct:.1f}%），其中{category} {category_count}单（{category_pct:.1f}%）"
    return f"品类偏好集中在{category}（{category_count}单，占{category_pct:.1f}%）"


def _format_discount_trait(discount_ratio: float, discount_sensitivity: str, promo: Dict[str, Any]) -> str:
    if discount_ratio >= 0.7:
        return f"折扣占比{discount_ratio:.0%}且集中在大促窗口，是明确的大促折扣心智客户，价格敏感度高"
    if discount_ratio >= 0.4:
        return f"折扣占比{discount_ratio:.0%}，叠加大促窗口集中购买，价格敏感度中高"
    if promo.get("share", 0) >= 0.5:
        return f"折扣占比{discount_ratio:.0%}、{discount_sensitivity}，更像固定在平台大促/季末节点集中购买，而不是纯低价驱动"
    return f"折扣占比{discount_ratio:.0%}、{discount_sensitivity}，价格驱动不强"


def _category_expansion_risk(top_category: Dict[str, Any], top_group: Dict[str, Any]) -> str:
    group = top_group.get("group", "")
    group_pct = float(top_group.get("percentage", 0) or 0)
    if group == "READYWEAR" and group_pct >= 80:
        return "品类高度集中在男士上装，皮具/配饰扩展空间仍需引导"
    category = top_category.get("category", "核心品类")
    return f"核心品类集中在{category}，跨品类扩展需要搭配场景牵引"


def _dedupe_nonempty(items: List[Any], limit: int) -> List[str]:
    seen = set()
    result = []
    for item in items:
        text = str(item).strip() if item is not None else ""
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if len(result) >= limit:
            break
    return result


def _calculate_order_span_days(dated_orders: List[Any]) -> int:
    if len(dated_orders) < 2:
        return 0
    first_dt = dated_orders[-1][0]
    last_dt = dated_orders[0][0]
    return max((last_dt - first_dt).days, 0)


def _build_spend_seasonality(year_breakdown: List[Dict[str, Any]], month_breakdown: List[Dict[str, Any]]) -> str:
    if not month_breakdown:
        return "无明确月份高峰"
    peak_months = ", ".join(item["month"] for item in month_breakdown[:3])
    peak_years = ", ".join(item["year"] for item in year_breakdown[:3]) if year_breakdown else ""
    if peak_years:
        return f"高峰集中在 {peak_years} 年及 {peak_months}"
    return f"高峰集中在 {peak_months}"


def analyze_purchase_features(profile: Dict, orders: List[Dict]) -> Dict[str, Any]:
    """分析购买特征"""
    category_distribution = calculate_category_distribution(orders)
    return {
        "首次购买品类": profile.get("top_category", "未知"),
        "真实品类分布": category_distribution,
        "品类阶段变化": category_distribution.get("stage_summary", ""),
        "品类集中度": calculate_category_focus(orders),
        "客单价趋势": calculate_price_trend(orders),
        "复购间隔": calculate_avg_interval(profile, orders),
        "首次购买时间": profile.get("first_purchase_date", ""),
        "最后购买时间": profile.get("last_purchase_date", ""),
        "总订单数": profile.get("total_orders", 0)
    }


def analyze_after_sales_behavior(profile: Dict, orders: List[Dict]) -> Dict[str, Any]:
    """分析售后行为"""
    # 计算退款率
    l6m_refund_rate = profile.get("l6m_refund_rate", 0) or 0
    total_refund_count = profile.get("total_refund_count", 0) or 0

    return {
        "退款率": f"{l6m_refund_rate:.1%}" if isinstance(l6m_refund_rate, (int, float)) else "0%",
        "退款次数": total_refund_count,
        "退货原因": analyze_refund_reasons(orders),
        "投诉次数": count_complaints(orders),
        "品质敏感度": judge_quality_sensitivity(l6m_refund_rate, total_refund_count)
    }


def analyze_communication_pattern(profile: Dict) -> Dict[str, Any]:
    """分析沟通特征"""
    chats = profile.get("chat_history", [])

    return {
        "主动咨询频率": profile.get("l3m_chat_frequency_days", 0),
        "沟通时机": analyze_communication_timing(profile),
        "问题类型分布": classify_chat_questions(chats),
        "语言风格": detect_language_style(chats),
        "新手信号数量": count_signals(chats, "rookie"),
        "专家信号数量": count_signals(chats, "expert")
    }


def analyze_value_metrics(profile: Dict) -> Dict[str, Any]:
    """分析价值特征"""
    l6m_netsales = profile.get("l6m_netsales", 0) or 0
    l1y_netsales = profile.get("l1y_netsales", 0) or 0
    historical_net_sales = profile.get("historical_net_sales", 0) or 0

    return {
        "VIP等级": profile.get("vip_level", "Non-VIP"),
        "L6M消费": f"¥{l6m_netsales:,.0f}",
        "L1Y消费": f"¥{l1y_netsales:,.0f}",
        "历史总消费": f"¥{historical_net_sales:,.0f}",
        "客单价": calculate_avg_order_price(profile),
        "消费趋势": calculate_consumption_trend(l6m_netsales, l1y_netsales)
    }


def calculate_category_focus(orders: List[Dict]) -> str:
    """
    计算品类集中度
    - 1个品类：专注型
    - 2个品类：偏好型
    - 3+品类：多样化
    """
    if not orders:
        return "未知"

    distribution = calculate_category_distribution(orders)
    categories = distribution.get("categories", [])

    if len(categories) == 0:
        return "未知"

    top = categories[0]
    top_ratio = top.get("percentage", 0)
    top_category = top.get("category", "未知")

    if top_ratio >= 99.5:
        return f"单一品类（{top_category} 100%）"
    if top_ratio >= 80:
        return f"品类专注型（{top_category} {top_ratio:.1f}%）"
    if len(categories) == 2:
        return f"双品类偏好（{distribution.get('summary', '')}）"
    return f"多品类（{distribution.get('summary', '')}）"


def calculate_category_distribution(orders: List[Dict]) -> Dict[str, Any]:
    """
    Calculate authoritative category distribution from raw order lines.

    This is intentionally based on the actual category field from target_buyer_orders.
    Do not collapse unknown categories into OTHER, because doing so can make the AI
    overstate category focus.
    """
    if not orders:
        return {
            "total_order_lines": 0,
            "categories": [],
            "category_groups": [],
            "yearly_categories": [],
            "summary": "无订单品类数据",
            "stage_summary": "无订单品类数据",
            "single_category": False,
            "top_category": "未知",
            "top_percentage": 0.0,
        }

    counts: Counter[str] = Counter()
    group_counts: Counter[str] = Counter()
    yearly_counts: Dict[str, Counter[str]] = {}
    for order in orders:
        category = normalize_category(order.get("category"))
        if category:
            counts[category] += 1
            group_counts[classify_category_group(category)] += 1

            year = extract_order_year(order)
            if year:
                yearly_counts.setdefault(year, Counter())[category] += 1

    if not counts:
        return {
            "total_order_lines": len(orders),
            "categories": [],
            "category_groups": [],
            "yearly_categories": [],
            "summary": "订单缺少category字段，不能判断品类占比",
            "stage_summary": "订单缺少category字段，不能判断品类阶段变化",
            "single_category": False,
            "top_category": "未知",
            "top_percentage": 0.0,
        }

    total = sum(counts.values())
    categories = [
        {
            "category": category,
            "order_lines": count,
            "percentage": round(count / total * 100, 1),
        }
        for category, count in counts.most_common()
    ]
    category_groups = [
        {
            "group": group,
            "order_lines": count,
            "percentage": round(count / total * 100, 1),
        }
        for group, count in group_counts.most_common()
    ]
    yearly_categories = []
    for year in sorted(yearly_counts):
        year_total = sum(yearly_counts[year].values())
        yearly_categories.append({
            "year": year,
            "total_order_lines": year_total,
            "categories": [
                {
                    "category": category,
                    "order_lines": count,
                    "percentage": round(count / year_total * 100, 1),
                }
                for category, count in yearly_counts[year].most_common()
            ],
        })
    summary = "、".join(
        f"{item['category']} {item['order_lines']}行/{item['percentage']}%"
        for item in categories
    )
    stage_summary = format_stage_summary(yearly_categories)

    return {
        "total_order_lines": total,
        "categories": categories,
        "category_groups": category_groups,
        "yearly_categories": yearly_categories,
        "summary": summary,
        "stage_summary": stage_summary,
        "single_category": len(categories) == 1,
        "top_category": categories[0]["category"],
        "top_percentage": categories[0]["percentage"],
    }


def normalize_category(category: Any) -> str:
    """Normalize category values while preserving the source category label."""
    if category is None:
        return ""
    value = str(category).strip()
    if not value or value.lower() in {"none", "null", "nan", "unknown"}:
        return ""
    return value.upper()


def extract_order_datetime(order: Dict[str, Any]) -> datetime | None:
    value = order.get("pay_time") or order.get("最后付款时间") or order.get("payment_time")
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:len(fmt)], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def classify_category_group(category: str) -> str:
    """Map source category labels into broad commercial groups without translating them."""
    value = normalize_category(category)
    readywear = {
        "KNITWEAR", "WOVEN OUTERWEAR", "CASUAL SHIRTS", "JACKETS", "JERSEY",
        "READYWEAR", "READY TO WEAR", "READY-TO-WEAR", "SUITS", "TROUSERS",
        "COATS", "SHIRTS", "T-SHIRTS", "POLO SHIRTS",
    }
    accessories = {
        "JEWELLERY", "BELTS", "TIES", "GIFTING", "EYEWEAR", "SCARVES",
        "HATS", "CUFFLINKS", "TIE CLIPS", "ACCESSORIES",
    }
    leather_goods = {
        "LARGE LEATHER", "SMALL LEATHER", "LEATHER GOODS", "BAGS",
        "WALLETS", "BRIEFCASES",
    }
    footwear = {"FOOTWEAR", "SHOES", "SNEAKERS", "BOOTS"}
    pipes_lighters = {"PIPES", "LIGHTERS", "SMOKING ACCESSORIES"}

    if value in readywear:
        return "READYWEAR"
    if value in accessories:
        return "ACCESSORIES/GIFTING"
    if value in leather_goods:
        return "LEATHER GOODS"
    if value in footwear:
        return "FOOTWEAR"
    if value in pipes_lighters:
        return "PIPES/LIGHTERS"
    return "OTHER"


def extract_order_year(order: Dict[str, Any]) -> str:
    """Extract payment year from common order timestamp fields."""
    value = order.get("pay_time") or order.get("最后付款时间") or order.get("payment_time")
    if not value:
        return ""
    if isinstance(value, datetime):
        return str(value.year)
    text = str(value)
    return text[:4] if len(text) >= 4 and text[:4].isdigit() else ""


def format_stage_summary(yearly_categories: List[Dict[str, Any]]) -> str:
    """Format yearly category migration facts for AI prompts."""
    if not yearly_categories:
        return "缺少付款年份，无法判断品类阶段变化"

    parts = []
    for year_item in yearly_categories:
        categories = year_item.get("categories", [])[:4]
        category_text = "、".join(
            f"{item['category']} {item['order_lines']}行"
            for item in categories
        )
        parts.append(f"{year_item.get('year')}: {category_text}")
    return "；".join(parts)


def calculate_price_trend(orders: List[Dict]) -> str:
    """
    分析客单价趋势
    """
    if not orders or len(orders) < 2:
        return "单次购买"

    # 提取所有订单的净销售额
    prices = []
    for order in orders:
        price = order.get("netsales", order.get("payment", 0))
        if price and price > 0:
            prices.append(price)

    if len(prices) < 2:
        return "单次购买"

    # 对比前半段和后半段的平均价格
    mid_point = len(prices) // 2
    first_half = prices[:mid_point]
    second_half = prices[mid_point:]

    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)

    if avg_second > avg_first * 1.2:
        return "上升"
    elif avg_second < avg_first * 0.8:
        return "下降"
    else:
        return "稳定"


def calculate_avg_interval(profile: Dict, orders: List[Dict]) -> str:
    """计算平均复购间隔"""
    first_purchase = profile.get("first_purchase_date")
    last_purchase = profile.get("last_purchase_date")
    total_orders = profile.get("total_orders", 0)

    if not first_purchase or not last_purchase or total_orders < 2:
        return "单次购买"

    try:
        # 计算购买天数跨度
        start = datetime.strptime(str(first_purchase)[:10], "%Y-%m-%d")
        end = datetime.strptime(str(last_purchase)[:10], "%Y-%m-%d")
        days_diff = (end - start).days

        if days_diff <= 0:
            return "单次购买"

        avg_days = days_diff / (total_orders - 1)

        if avg_days < 30:
            return f"{int(avg_days)}天（高频）"
        elif avg_days < 90:
            return f"{int(avg_days)}天（中频）"
        else:
            return f"{int(avg_days)}天（低频）"

    except Exception:
        return "未知"


def analyze_refund_reasons(orders: List[Dict]) -> str:
    """分析退款原因"""
    if not orders:
        return "无退款"

    refund_orders = [o for o in orders if o.get("refund_status") == "是"]

    if not refund_orders:
        return "无退款"

    # 这里可以根据实际情况分析退款原因
    # 暂时返回简单统计
    return f"{len(refund_orders)}次退款（品质要求高/不匹配等）"


def count_complaints(orders: List[Dict]) -> int:
    """统计投诉次数"""
    # 可以从聊天记录或订单备注中提取
    # 暂时返回0
    return 0


def judge_quality_sensitivity(refund_rate: float, refund_count: int) -> str:
    """判断品质敏感度"""
    if refund_rate > 0.1 or refund_count >= 3:
        return "高（对品质要求严格）"
    elif refund_rate > 0.05 or refund_count >= 1:
        return "中（有一定品质要求）"
    else:
        return "低（容易满足）"


def analyze_communication_timing(profile: Dict) -> str:
    """分析沟通时机"""
    # 可以分析聊天时间分布（工作日/周末，白天/晚上）
    # 暂时返回简单描述
    return "根据购买后咨询判断"


def classify_chat_questions(chats: List[Dict]) -> str:
    """分类聊天问题"""
    if not chats:
        return "无聊天记录"

    # 简单统计
    types = []
    for chat in chats:
        content = chat.get("content", "")

        if any(word in content for word in ["怎么用", "如何", "不懂"]):
            types.append("使用指导")
        elif any(word in content for word in ["推荐", "哪个好", "怎么选"]):
            types.append("寻求推荐")
        elif any(word in content for word in ["多少钱", "价格", "折扣"]):
            types.append("价格咨询")

    if not types:
        return "日常交流"

    # 返回最主要的类型
    from collections import Counter
    most_common = Counter(types).most_common(1)[0][0]
    return most_common


def detect_language_style(chats: List[Dict]) -> str:
    """
    检测客户语言风格
    - 新手口语：大量疑问句、语气词
    - 专业术语：使用行业术语
    - 日常交流：简单直接
    """
    if not chats:
        return "未知"

    # 专家信号关键词
    EXPERT_SIGNALS_TERMS = [
        "finish", "briar", "grain", "吸阻", "过滤",
        "产地", "工艺", "材质", "型号"
    ]

    # 新手信号关键词
    ROOKIE_SIGNALS = [
        "新手", "小白", "第一次", "不太懂", "不知道", "怎么样",
        "推荐", "哪个好", "怎么选", "求指导"
    ]

    question_count = 0
    term_count = 0

    for chat in chats:
        content = chat.get("content", "")

        if "？" in content or "?" in content:
            question_count += 1

        if any(term in content for term in EXPERT_SIGNALS_TERMS):
            term_count += 1

    if question_count / len(chats) > 0.5:
        return "新手口语"
    elif term_count / len(chats) > 0.3:
        return "专业术语"
    else:
        return "日常交流"


def count_signals(chats: List[Dict], signal_type: str) -> int:
    """统计信号数量"""
    if not chats:
        return 0

    count = 0
    for chat in chats:
        content = chat.get("content", "")

        if signal_type == "rookie":
            if detect_rookie_signal(content):
                count += 1
        elif signal_type == "expert":
            if detect_expert_signal(content):
                count += 1

    return count


def calculate_avg_order_price(profile: Dict) -> str:
    """计算客单价"""
    total_orders = profile.get("total_orders", 0)
    historical_net_sales = profile.get("historical_net_sales", 0) or 0

    if total_orders == 0:
        return "¥0"

    avg_price = historical_net_sales / total_orders
    return f"¥{avg_price:,.0f}"


def calculate_consumption_trend(l6m: float, l1y: float) -> str:
    """计算消费趋势"""
    if l6m == 0 or l1y == 0:
        return "稳定"

    # L6M是最近6个月，L1Y是最近1年
    # 如果L6M占L1Y比例超过50%，说明消费在上升
    ratio = l6m / l1y if l1y > 0 else 0

    if ratio > 0.6:
        return "上升（最近活跃）"
    elif ratio < 0.3:
        return "下降（活跃度降低）"
    else:
        return "稳定"
