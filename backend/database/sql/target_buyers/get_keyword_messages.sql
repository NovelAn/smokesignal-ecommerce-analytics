SELECT
    ch.user_nick AS buyer_nick,
    tb.buyer_type,
    ch.content,
    ch.msg_time
FROM chat_history ch
JOIN target_buyers_precomputed tb ON tb.buyer_nick = ch.user_nick
WHERE ch.sender_nick = ch.user_nick
  AND ch.content IS NOT NULL
  AND ch.content <> ''
  AND ch.msg_time >= %(start_date)s
  AND ch.msg_time < DATE_ADD(%(end_date)s, INTERVAL 1 DAY)
  [[AND tb.buyer_type IN %(buyer_types)s]]
ORDER BY ch.msg_time DESC;
