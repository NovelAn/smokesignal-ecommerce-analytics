SELECT id, buyer_nick, workstream, status, notes, created_at, updated_at
FROM customer_service_log
WHERE buyer_nick = %s
  AND workstream = %s
ORDER BY updated_at DESC;
