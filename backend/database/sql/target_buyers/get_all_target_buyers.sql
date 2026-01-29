-- ============================================
-- 获取所有目标买家列表(分页)
-- ============================================
-- 用途: 前端买家列表页
-- 性能: < 0.5秒
-- 参数: search, buyer_type, vip_level, channel, sort_by, limit, offset
-- 注意: 这个SQL会被Python代码动态构建WHERE子句
-- ============================================

SELECT
    buyer_nick,
    channel,
    buyer_type,
    is_smoker,
    is_vic,
    vip_level,
    client_monthly_tag,
    historical_net_sales,
    total_orders,
    l6m_netsales,
    l6m_orders,
    l1y_netsales,
    l1y_orders,
    city,
    top_category,
    churn_risk,
    l3m_chat_frequency_days,
    last_purchase_date
FROM target_buyers_precomputed
WHERE 1=1
    [[AND buyer_nick LIKE %(search)s]]
    [[AND buyer_type IN %(buyer_type)s]]
    [[AND vip_level IN %(vip_level)s]]
    [[AND channel IN %(channel)s]]
    [[AND last_purchase_date >= %(last_purchase_after)s]]
    [[AND last_chat_date IS NOT NULL AND %(chat_status)s = 'chatted']]
    [[AND last_chat_date IS NULL AND %(chat_status)s = 'no_chat']]
    AND NOT EXISTS (
        SELECT 1 
        FROM target_buyer_orders tbo 
        WHERE tbo.买家昵称 = target_buyers_precomputed.buyer_nick 
        AND (tbo.sc_flag = 1 OR tbo.ff_flag = 1)
    )
ORDER BY
    CASE
        WHEN %(sort_by)s = 'last_purchase' THEN last_purchase_date
        WHEN %(sort_by)s = 'l6m_netsales' THEN l6m_netsales
        WHEN %(sort_by)s = 'vip_level' THEN
            CASE vip_level
                WHEN 'V3' THEN 5
                WHEN 'V2' THEN 4
                WHEN 'V1' THEN 3
                WHEN 'V0' THEN 2
                ELSE 1
            END
        ELSE last_purchase_date
    END DESC
LIMIT %(limit)s OFFSET %(offset)s;
