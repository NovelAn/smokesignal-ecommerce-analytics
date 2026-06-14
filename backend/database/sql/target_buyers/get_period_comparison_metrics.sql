WITH boundaries AS (
    SELECT
        (
            SELECT MAX(snapshot_date)
            FROM target_buyers_precomputed_history
            WHERE snapshot_date < %(start_date)s
        ) AS baseline_date,
        (
            SELECT MAX(snapshot_date)
            FROM target_buyers_precomputed_history
            WHERE snapshot_date <= %(end_date)s
        ) AS end_date
),
period_pairs AS (
    SELECT
        h_end.buyer_nick,
        h_end.buyer_type AS buyer_type_end,
        h_base.buyer_type AS buyer_type_base,
        h_end.churn_risk AS churn_risk_end,
        h_base.churn_risk AS churn_risk_base,
        h_end.vip_level AS vip_level_end,
        h_base.vip_level AS vip_level_base
    FROM boundaries b
    JOIN target_buyers_precomputed_history h_end
        ON h_end.snapshot_date = b.end_date
    LEFT JOIN target_buyers_precomputed_history h_base
        ON h_base.buyer_nick = h_end.buyer_nick
        AND h_base.snapshot_date = b.baseline_date
)
SELECT
    COALESCE(SUM(
        buyer_type_end IN ('VIC', 'BOTH')
        AND (buyer_type_base IS NULL OR buyer_type_base NOT IN ('VIC', 'BOTH'))
    ), 0) AS new_vic,
    COALESCE(SUM(
        churn_risk_base IN ('低', '中')
        AND churn_risk_end = '高'
    ), 0) AS churn_warning,
    COALESCE(SUM(
        vip_level_base IS NOT NULL
        AND CASE vip_level_end
            WHEN 'V3' THEN 4 WHEN 'V2' THEN 3 WHEN 'V1' THEN 2
            WHEN 'V0' THEN 1 ELSE 0
        END
        >
        CASE vip_level_base
            WHEN 'V3' THEN 4 WHEN 'V2' THEN 3 WHEN 'V1' THEN 2
            WHEN 'V0' THEN 1 ELSE 0
        END
    ), 0) AS vip_upgrades,
    (
        SELECT COUNT(*)
        FROM buyer_ai_analysis_cache ai
        WHERE ai.incremental_sentiment_label = 'Negative'
          AND COALESCE(
              ai.incremental_sentiment_analyzed_at,
              ai.incremental_chat_to_date
          ) >= %(start_date)s
          AND COALESCE(
              ai.incremental_sentiment_analyzed_at,
              ai.incremental_chat_to_date
          ) < DATE_ADD(%(end_date)s, INTERVAL 1 DAY)
    ) AS sentiment_negative
FROM period_pairs
