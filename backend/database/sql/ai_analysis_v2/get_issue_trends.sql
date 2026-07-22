-- name: get_issue_trends.sql
SELECT grouped.*,
    CASE
        WHEN grouped.previous_period_count = 0 AND grouped.current_period_count > 0 THEN 100.0
        WHEN grouped.previous_period_count = 0 THEN 0.0
        ELSE ROUND(
            (grouped.current_period_count - grouped.previous_period_count)
            * 100.0 / grouped.previous_period_count,
            1
        )
    END AS change_percent
FROM (
    SELECT
        i.issue_category,
        i.issue_code,
        COUNT(DISTINCT i.event_id) AS event_count,
        COUNT(DISTINCT i.buyer_nick) AS affected_buyers,
        SUM(i.status <> 'resolved') AS unresolved_count,
        SUM(i.severity IN ('high','critical')) AS high_severity_count,
        MAX(i.created_at) AS last_seen_at,
        COUNT(DISTINCT CASE WHEN i.created_at >= %s AND i.created_at < %s THEN i.event_id END) AS current_period_count,
        COUNT(DISTINCT CASE WHEN i.created_at >= %s AND i.created_at < %s THEN i.event_id END) AS previous_period_count
    FROM ai_analysis_v2_issues i
    WHERE i.created_at >= %s AND i.created_at < %s
    [[OPTIONAL_CONDITION]]
    GROUP BY i.issue_category, i.issue_code
) grouped
ORDER BY grouped.affected_buyers DESC, grouped.event_count DESC;
