-- name: select_review_candidates.sql
WITH event_features AS (
    SELECT
        e.id AS event_id,
        e.buyer_nick,
        e.sentiment_label,
        e.sentiment_basis,
        e.service_friction,
        e.event_ended_at,
        MAX(i.severity = 'critical') AS has_critical,
        MAX(i.severity = 'high') AS has_high,
        MAX(i.issue_category IN ('product','after_sales')) AS has_product_after_sales,
        MAX(i.issue_category IN ('logistics','pricing_promotion','inventory','service')) AS has_operations_friction,
        MAX(i.issue_code IN ('authenticity_concern','color_appearance_mismatch','advertising_mismatch')) AS has_ambiguity
    FROM ai_analysis_v2_events e
    LEFT JOIN ai_analysis_v2_issues i ON i.event_id = e.id
    GROUP BY e.id, e.buyer_nick, e.sentiment_label, e.sentiment_basis,
             e.service_friction, e.event_ended_at
)
SELECT
    event_id,
    buyer_nick,
    CASE
        WHEN sentiment_label = 'Negative' THEN 'negative'
        WHEN has_ambiguity = 1 OR sentiment_basis = 'authenticity_concern' THEN 'ambiguity'
        WHEN has_product_after_sales = 1 THEN 'product_after_sales'
        WHEN has_operations_friction = 1 OR service_friction IN ('medium','high') THEN 'operations_friction'
        ELSE 'baseline'
    END AS stratum,
    (CASE WHEN sentiment_label = 'Negative' THEN 40 ELSE 0 END
     + CASE WHEN has_critical = 1 THEN 30 WHEN has_high = 1 THEN 20 ELSE 0 END
     + GREATEST(0, 30 - DATEDIFF(CURRENT_DATE, event_ended_at))) AS risk_score
FROM event_features
ORDER BY risk_score DESC, event_ended_at DESC;
