-- name: get_acceptance_reviews.sql
SELECT review_status, model_payload, gold_payload
FROM ai_analysis_v2_reviews
ORDER BY id;
