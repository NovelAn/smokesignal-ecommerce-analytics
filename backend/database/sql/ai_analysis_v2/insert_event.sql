-- name: insert_event.sql
INSERT INTO ai_analysis_v2_events (
    buyer_nick, created_run_id, last_run_id, event_index, topic_summary,
    event_started_at, event_ended_at, sentiment_label, sentiment_score,
    sentiment_basis, peak_emotion, service_friction, resolution_status,
    customer_accepted, suggested_action
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
