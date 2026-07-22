-- name: upsert_review.sql
INSERT INTO ai_analysis_v2_reviews (
    event_id, review_stratum, review_status, model_payload
)
VALUES (%s, %s, 'pending', %s)
ON DUPLICATE KEY UPDATE
    review_stratum = VALUES(review_stratum),
    model_payload = IF(review_status = 'pending', VALUES(model_payload), model_payload);
