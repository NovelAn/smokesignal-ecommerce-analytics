-- name: review_event.sql
INSERT INTO ai_analysis_v2_reviews (
    event_id, review_status, model_payload, gold_payload,
    review_note, reviewed_by, reviewed_at
)
VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
ON DUPLICATE KEY UPDATE
    review_status = VALUES(review_status),
    gold_payload = VALUES(gold_payload),
    review_note = VALUES(review_note),
    reviewed_by = VALUES(reviewed_by),
    reviewed_at = VALUES(reviewed_at);
