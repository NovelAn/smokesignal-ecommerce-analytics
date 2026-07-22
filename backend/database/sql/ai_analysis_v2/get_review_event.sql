-- name: get_review_event.sql
SELECT id, buyer_nick, last_run_id
FROM ai_analysis_v2_events
WHERE id = %s
LIMIT 1
FOR UPDATE;
