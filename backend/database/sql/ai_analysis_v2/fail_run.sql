-- name: fail_run.sql
UPDATE ai_analysis_v2_runs
SET status = 'failed', result_payload = NULL, completed_fingerprint = NULL,
    failure_code = %s, failure_message = %s, completed_at = CURRENT_TIMESTAMP
WHERE id = %s;
