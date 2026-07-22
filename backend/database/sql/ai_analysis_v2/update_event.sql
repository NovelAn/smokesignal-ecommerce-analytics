-- name: update_event.sql
UPDATE ai_analysis_v2_events
SET last_run_id = %s, topic_summary = %s, event_started_at = %s,
    event_ended_at = %s, sentiment_label = %s, sentiment_score = %s,
    sentiment_basis = %s, peak_emotion = %s, service_friction = %s,
    resolution_status = %s, customer_accepted = %s, suggested_action = %s
WHERE id = %s AND buyer_nick = %s;
