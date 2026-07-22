-- name: get_buyer_profile.sql
SELECT *
FROM target_buyers_precomputed
WHERE buyer_nick = %s
LIMIT 1;
