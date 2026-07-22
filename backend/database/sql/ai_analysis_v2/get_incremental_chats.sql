-- name: get_incremental_chats.sql
SELECT * FROM (
    SELECT user_nick, sender_nick, msg_time, msg_type, content
    FROM chat_history
    WHERE user_nick = %s AND msg_time > %s
    UNION ALL
    SELECT * FROM (
        SELECT user_nick, sender_nick, msg_time, msg_type, content
        FROM chat_history
        WHERE user_nick = %s AND msg_time <= %s
        ORDER BY msg_time DESC
        LIMIT 20
    ) context_rows
) source_rows
ORDER BY msg_time ASC;
