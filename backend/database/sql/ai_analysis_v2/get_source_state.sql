-- name: get_source_state.sql
SELECT *
FROM ai_analysis_v2_customer_state
WHERE buyer_nick = %s
LIMIT 1;
