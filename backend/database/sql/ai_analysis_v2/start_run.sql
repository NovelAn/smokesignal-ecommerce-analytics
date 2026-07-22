-- name: start_run.sql
INSERT INTO ai_analysis_v2_runs (
    buyer_nick, analysis_mode, provider, model, prompt_version,
    source_fingerprint, source_from_msg_time, source_to_msg_time, source_message_count
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
