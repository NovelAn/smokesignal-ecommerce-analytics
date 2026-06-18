-- 统一流失预警：历史退化、购买力坍塌、真实增量情感转负
WITH snapshot_dates AS (
    SELECT
        MAX(snapshot_date) AS latest_date,
        COALESCE(
            MAX(CASE
                WHEN snapshot_date <= DATE_SUB(
                    (SELECT MAX(snapshot_date) FROM target_buyers_precomputed_history),
                    INTERVAL %(window_days)s DAY
                )
                THEN snapshot_date
            END),
            MIN(snapshot_date)
        ) AS previous_date
    FROM target_buyers_precomputed_history
),
signal_rows AS (
    SELECT
        h_now.buyer_nick,
        tb.channel,
        tb.buyer_type,
        tb.vip_level,
        h_prev.rfm_segment AS segment_prev,
        h_now.rfm_segment AS segment_now,
        h_prev.churn_risk AS churn_risk_prev,
        h_now.churn_risk AS churn_risk_now,
        h_prev.l6m_netsales AS l6m_netsales_prev,
        h_now.l6m_netsales AS l6m_netsales_now,
        tb.last_purchase_date,
        tb.last_chat_date,
        csl.status AS service_status,
        csl.updated_at AS service_updated_at,
        csl.notes AS service_notes,
        d.latest_date,
        (
            h_prev.rfm_segment IN (
                '重要价值客户', '重要保持客户', '重要发展客户',
                '优质价值客户', '优质保持客户', '优质发展客户'
            )
            AND h_now.rfm_segment IN (
                '潜力客户', '待激活客户', '已流失', '低价值客户',
                '重要挽留客户', '优质挽留客户'
            )
        ) AS cond_segment,
        (
            h_prev.rfm_segment IN ('重要价值客户', '重要保持客户')
            AND h_now.rfm_segment IN ('已流失', '低价值客户')
        ) AS cond_segment_severe,
        (
            h_prev.churn_risk IN ('低', '中')
            AND h_now.churn_risk = '高'
        ) AS cond_churn,
        (
            h_prev.l6m_netsales >= %(l6m_floor)s
            AND h_now.l6m_netsales - h_prev.l6m_netsales
                <= -0.5 * h_prev.l6m_netsales
        ) AS cond_sales,
        (
            ai.incremental_sentiment_label = 'Negative'
            AND COALESCE(
                ai.incremental_sentiment_analyzed_at,
                ai.incremental_chat_to_date
            ) >= DATE_SUB(d.latest_date, INTERVAL %(window_days)s DAY)
            AND COALESCE(
                ai.incremental_sentiment_analyzed_at,
                ai.incremental_chat_to_date
            ) < DATE_ADD(d.latest_date, INTERVAL 1 DAY)
        ) AS cond_sentiment,
        (
            csl.id IS NULL
            OR csl.status = 'pending'
            OR (
                csl.status IN ('contacted', 'resolved')
                AND (
                    (
                        ai.incremental_sentiment_label = 'Negative'
                        AND COALESCE(
                            ai.incremental_sentiment_analyzed_at,
                            ai.incremental_chat_to_date
                        ) > csl.updated_at
                    )
                    OR (
                        h_service.snapshot_date IS NOT NULL
                        AND (
                            (
                                h_service.rfm_segment IN (
                                    '重要价值客户', '重要保持客户', '重要发展客户',
                                    '优质价值客户', '优质保持客户', '优质发展客户'
                                )
                                AND h_now.rfm_segment IN (
                                    '潜力客户', '待激活客户', '已流失', '低价值客户',
                                    '重要挽留客户', '优质挽留客户'
                                )
                            )
                            OR (
                                h_service.churn_risk IN ('低', '中')
                                AND h_now.churn_risk = '高'
                            )
                            OR (
                                h_service.l6m_netsales >= %(l6m_floor)s
                                AND h_now.l6m_netsales - h_service.l6m_netsales
                                    <= -0.5 * h_service.l6m_netsales
                            )
                        )
                    )
                )
            )
        ) AS is_trackable
    FROM snapshot_dates d
    JOIN target_buyers_precomputed_history h_now
        ON h_now.snapshot_date = d.latest_date
    JOIN target_buyers_precomputed_history h_prev
        ON h_prev.buyer_nick = h_now.buyer_nick
        AND h_prev.snapshot_date = d.previous_date
    JOIN target_buyers_precomputed tb
        ON tb.buyer_nick = h_now.buyer_nick
    LEFT JOIN buyer_ai_analysis_cache ai
        ON ai.buyer_nick = h_now.buyer_nick
    LEFT JOIN customer_service_log csl
        ON csl.buyer_nick = h_now.buyer_nick
        AND csl.workstream = 'priority'
    LEFT JOIN target_buyers_precomputed_history h_service
        ON h_service.buyer_nick = h_now.buyer_nick
        AND h_service.snapshot_date = (
            SELECT MAX(hs.snapshot_date)
            FROM target_buyers_precomputed_history hs
            WHERE hs.buyer_nick = h_now.buyer_nick
              AND hs.snapshot_date <= DATE(csl.updated_at)
        )
),
qualified AS (
    SELECT *
    FROM signal_rows
    WHERE (cond_segment OR cond_churn OR cond_sales OR cond_sentiment)
      AND is_trackable
)
SELECT
    buyer_nick,
    channel,
    buyer_type,
    vip_level,
    segment_prev,
    segment_now,
    churn_risk_prev,
    churn_risk_now,
    ROUND(l6m_netsales_now - l6m_netsales_prev, 2) AS l6m_netsales_change,
    ROUND(
        (l6m_netsales_now - l6m_netsales_prev)
        / NULLIF(l6m_netsales_prev, 0) * 100,
        1
    ) AS l6m_change_pct,
    last_purchase_date,
    last_chat_date,
    service_status,
    service_updated_at,
    service_notes,
    TRIM(BOTH ',' FROM CONCAT_WS(',',
        IF(cond_segment, 'segment退化', NULL),
        IF(cond_churn, 'churn高风险', NULL),
        IF(cond_sales, '购买力坍塌', NULL),
        IF(cond_sentiment, '情感转负', NULL)
    )) AS selection_reasons,
    CASE
        WHEN cond_sentiment OR cond_segment_severe THEN 1
        WHEN cond_churn AND NOT cond_sales THEN 2
        WHEN cond_segment AND NOT cond_churn AND NOT cond_sales THEN 2
        WHEN cond_sales OR cond_segment THEN 3
        ELSE 4
    END AS severity_tier,
    COUNT(*) OVER() AS total_count
FROM qualified
ORDER BY
    severity_tier ASC,
    (l6m_netsales_now - l6m_netsales_prev) ASC,
    last_purchase_date DESC
LIMIT %(limit)s OFFSET %(offset)s
