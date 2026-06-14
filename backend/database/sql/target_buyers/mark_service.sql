INSERT INTO customer_service_log (buyer_nick, workstream, status, notes)
VALUES (%s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    status = VALUES(status),
    notes = VALUES(notes),
    updated_at = CURRENT_TIMESTAMP;
