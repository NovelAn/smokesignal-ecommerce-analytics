-- name: get_affected_buyers.sql
SELECT
    i.buyer_nick,
    i.issue_detail,
    i.severity,
    i.status,
    e.sentiment_label,
    e.event_ended_at
FROM ai_analysis_v2_issues i
JOIN ai_analysis_v2_events e ON e.id = i.event_id
WHERE i.issue_code = %s AND i.created_at >= %s AND i.created_at < %s
ORDER BY e.event_ended_at DESC;
