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
    SUM(h.buyer_type = 'SMOKER') AS SMOKER,
    SUM(h.buyer_type = 'VIC') AS VIC,
    SUM(h.buyer_type = 'BOTH') AS `BOTH`
FROM monthly_latest ml
JOIN target_buyers_precomputed_history h
    ON h.snapshot_date = ml.snapshot_date
GROUP BY ml.month
ORDER BY ml.month
