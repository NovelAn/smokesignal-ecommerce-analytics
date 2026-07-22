-- name: get_batch_candidates.sql
SELECT tb.buyer_nick
FROM target_buyers_precomputed tb
LEFT JOIN ai_analysis_v2_customer_state state ON state.buyer_nick = tb.buyer_nick
WHERE state.buyer_nick IS NULL
   OR EXISTS (
       SELECT 1
       FROM chat_history chat
       WHERE chat.user_nick = tb.buyer_nick
         AND chat.msg_time > state.analyzed_through_msg_time
   )
ORDER BY tb.last_chat_date DESC
LIMIT %s;
