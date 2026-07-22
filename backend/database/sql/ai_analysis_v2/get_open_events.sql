-- name: get_open_events.sql
SELECT id, topic_summary, event_started_at, event_ended_at,
       resolution_status, suggested_action
FROM ai_analysis_v2_events
WHERE buyer_nick = %s AND resolution_status <> 'resolved'
ORDER BY event_ended_at DESC;
