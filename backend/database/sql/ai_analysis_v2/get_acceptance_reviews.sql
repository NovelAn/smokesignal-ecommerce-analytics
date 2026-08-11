-- name: get_acceptance_reviews.sql
SELECT r.review_status, r.model_payload, r.gold_payload,
       e.buyer_nick, e.event_started_at, e.event_ended_at
FROM ai_analysis_v2_reviews r
JOIN ai_analysis_v2_events e ON e.id = r.event_id
ORDER BY r.id;
