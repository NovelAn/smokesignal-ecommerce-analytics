-- name: get_full_chats.sql
SELECT * FROM (
    SELECT user_nick, sender_nick, msg_time, msg_type, content
    FROM chat_history
    WHERE user_nick = %s
    ORDER BY msg_time DESC
    LIMIT 50
) recent
ORDER BY msg_time ASC;
