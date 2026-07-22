-- name: get_review_model_payload.sql
SELECT JSON_OBJECT(
    'events', JSON_ARRAY(JSON_OBJECT(
        'event_action', 'new_event',
        'related_event_id', NULL,
        'topic_summary', e.topic_summary,
        'event_started_at', e.event_started_at,
        'event_ended_at', e.event_ended_at,
        'sentiment_label', e.sentiment_label,
        'sentiment_score', e.sentiment_score,
        'sentiment_basis', e.sentiment_basis,
        'peak_emotion', e.peak_emotion,
        'service_friction', e.service_friction,
        'resolution_status', e.resolution_status,
        'customer_accepted', e.customer_accepted,
        'suggested_action', e.suggested_action,
        'issues', COALESCE((
            SELECT JSON_ARRAYAGG(JSON_OBJECT(
                'issue_category', i.issue_category,
                'issue_code', i.issue_code,
                'issue_detail', i.issue_detail,
                'severity', i.severity,
                'owner', i.owner,
                'status', i.status,
                'is_primary', i.is_primary,
                'evidence_text', i.evidence_text,
                'evidence_msg_time', i.evidence_msg_time
            ))
            FROM ai_analysis_v2_issues i
            WHERE i.event_id = e.id
        ), JSON_ARRAY())
    ))
) AS model_payload
FROM ai_analysis_v2_events e
WHERE e.id = %s;
