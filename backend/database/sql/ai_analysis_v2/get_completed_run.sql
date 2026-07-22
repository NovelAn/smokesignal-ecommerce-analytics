-- name: get_completed_run.sql
SELECT id, provider, model, result_payload
FROM ai_analysis_v2_runs
WHERE buyer_nick = %s AND completed_fingerprint = %s AND prompt_version = %s
  AND status = 'completed'
LIMIT 1;
