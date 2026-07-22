-- name: complete_run.sql
UPDATE ai_analysis_v2_runs
SET status = 'completed', completed_fingerprint = source_fingerprint,
    result_payload = %s, failure_code = NULL, failure_message = NULL,
    completed_at = CURRENT_TIMESTAMP
WHERE id = %s;
