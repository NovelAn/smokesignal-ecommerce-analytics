-- name: delete_event_issues.sql
DELETE FROM ai_analysis_v2_issues
WHERE event_id = %s;
