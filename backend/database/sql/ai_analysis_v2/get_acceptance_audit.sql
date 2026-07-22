-- name: get_acceptance_audit.sql
SELECT
    (SELECT COUNT(*) FROM ai_analysis_v2_runs
     WHERE status = 'failed' AND result_payload IS NOT NULL) AS failed_result_count,
    (SELECT COALESCE(SUM(grouped.row_count - 1), 0)
     FROM (
         SELECT COUNT(*) AS row_count
         FROM ai_analysis_v2_events
         GROUP BY created_run_id, event_index
         HAVING COUNT(*) > 1
     ) grouped) AS duplicate_event_count;
