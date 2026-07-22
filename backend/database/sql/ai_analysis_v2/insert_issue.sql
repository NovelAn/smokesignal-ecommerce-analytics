-- name: insert_issue.sql
INSERT INTO ai_analysis_v2_issues (
    event_id, buyer_nick, issue_category, issue_code, issue_detail,
    severity, owner, status, is_primary, evidence_text, evidence_msg_time
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
