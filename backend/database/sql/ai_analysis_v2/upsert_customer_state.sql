-- name: upsert_customer_state.sql
INSERT INTO ai_analysis_v2_customer_state (
    buyer_nick, current_sentiment_label, primary_issue_code, primary_issue_detail,
    active_issue_count, highest_severity, attention_priority, recommended_action,
    analyzed_through_msg_time, last_event_at, last_run_id
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    current_sentiment_label = VALUES(current_sentiment_label),
    primary_issue_code = VALUES(primary_issue_code),
    primary_issue_detail = VALUES(primary_issue_detail),
    active_issue_count = VALUES(active_issue_count),
    highest_severity = VALUES(highest_severity),
    attention_priority = VALUES(attention_priority),
    recommended_action = VALUES(recommended_action),
    analyzed_through_msg_time = VALUES(analyzed_through_msg_time),
    last_event_at = VALUES(last_event_at),
    last_run_id = VALUES(last_run_id);
