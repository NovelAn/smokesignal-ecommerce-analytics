WITH monthly_latest AS (
    SELECT
        DATE_FORMAT(snapshot_date, '%%Y-%%m') AS month,
        MAX(snapshot_date) AS snapshot_date
    FROM target_buyers_precomputed_history
    WHERE snapshot_date >= DATE_SUB(CURDATE(), INTERVAL %(months)s MONTH)
    GROUP BY DATE_FORMAT(snapshot_date, '%%Y-%%m')
)
SELECT
    ml.month,
    COUNT(*) AS total_vic,
    SUM(
        DATE_FORMAT(h.last_purchase_date, '%%Y-%%m') = ml.month
    ) AS active_vic
FROM monthly_latest ml
JOIN target_buyers_precomputed_history h
    ON h.snapshot_date = ml.snapshot_date
WHERE h.buyer_type IN ('VIC', 'BOTH')
GROUP BY ml.month
ORDER BY ml.month
