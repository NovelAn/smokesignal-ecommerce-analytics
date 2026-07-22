-- name: get_buyer_analysis.sql
SELECT
    (SELECT JSON_OBJECT(
        'buyer_nick', s.buyer_nick,
        'current_sentiment_label', s.current_sentiment_label,
        'primary_issue_code', s.primary_issue_code,
        'primary_issue_detail', s.primary_issue_detail,
        'active_issue_count', s.active_issue_count,
        'highest_severity', s.highest_severity,
        'attention_priority', s.attention_priority,
        'recommended_action', s.recommended_action,
        'analyzed_through_msg_time', s.analyzed_through_msg_time,
        'last_event_at', s.last_event_at,
        'last_run_id', s.last_run_id
    ) FROM ai_analysis_v2_customer_state s WHERE s.buyer_nick = %s) AS customer_state,
    (SELECT COALESCE(JSON_ARRAYAGG(JSON_OBJECT(
        'id', e.id, 'topic_summary', e.topic_summary,
        'event_started_at', e.event_started_at, 'event_ended_at', e.event_ended_at,
        'sentiment_label', e.sentiment_label, 'sentiment_score', e.sentiment_score,
        'sentiment_basis', e.sentiment_basis, 'peak_emotion', e.peak_emotion,
        'service_friction', e.service_friction, 'resolution_status', e.resolution_status,
        'customer_accepted', e.customer_accepted, 'suggested_action', e.suggested_action
    )), JSON_ARRAY()) FROM ai_analysis_v2_events e WHERE e.buyer_nick = %s) AS events,
    (SELECT COALESCE(JSON_ARRAYAGG(JSON_OBJECT(
        'id', i.id, 'event_id', i.event_id, 'issue_category', i.issue_category,
        'issue_code', i.issue_code, 'issue_detail', i.issue_detail,
        'severity', i.severity, 'owner', i.owner, 'status', i.status,
        'is_primary', i.is_primary, 'evidence_text', i.evidence_text,
        'evidence_msg_time', i.evidence_msg_time
    )), JSON_ARRAY()) FROM ai_analysis_v2_issues i WHERE i.buyer_nick = %s) AS issues;
