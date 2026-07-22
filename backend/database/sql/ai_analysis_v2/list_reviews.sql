-- name: list_reviews.sql
SELECT r.id, r.event_id, r.review_status, r.model_payload, r.gold_payload,
       r.review_note, r.reviewed_by, r.reviewed_at,
       e.buyer_nick, e.topic_summary, e.event_started_at, e.event_ended_at
FROM ai_analysis_v2_reviews r
JOIN ai_analysis_v2_events e ON e.id = r.event_id
ORDER BY r.id
LIMIT %s OFFSET %s;
