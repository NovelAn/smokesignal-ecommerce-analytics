"""Action API routes — customer demand action endpoints.

v2 routes surfacing actionable customer segments. Currently exposes
inventory-inquiry buyers so ops can act on stock / restock demand.
"""
import json

from fastapi import APIRouter, HTTPException

from backend.database import Database

router = APIRouter(prefix="/api/v2/action", tags=["action"])


@router.get("/inventory-inquiries")
async def get_inventory_inquiries():
    """库存需求客户列表：dominant_intent 为 Inventory Inquiry 或其意图占比 > 0.3。

    按客户 VIP 级别（V3→V0）优先排序，同级按最近沟通时间倒序。
    当前依赖 buyer_ai_analysis_cache 的意图分析；历史未回填，结果随新会话分析逐步填充。
    """
    try:
        db = Database()
        # NOTE: chat_history uses `user_nick` (not buyer_nick); instead of a fragile
        # correlated subquery we read total_chat_messages directly from the
        # precomputed table, which already stores it.
        query = """
            SELECT
                tb.buyer_nick, tb.vip_level, tb.last_chat_date,
                tb.total_chat_messages,
                ai.dominant_intent, ai.intent_distribution, ai.sentiment_label
            FROM target_buyers_precomputed tb
            JOIN buyer_ai_analysis_cache ai ON tb.buyer_nick = ai.buyer_nick
            WHERE ai.dominant_intent = 'Inventory Inquiry'
               OR JSON_EXTRACT(ai.intent_distribution, '$."Inventory Inquiry"') > 0.3
            ORDER BY
                CASE tb.vip_level
                    WHEN 'V3' THEN 1
                    WHEN 'V2' THEN 2
                    WHEN 'V1' THEN 3
                    WHEN 'V0' THEN 4
                    ELSE 5
                END ASC,
                tb.last_chat_date DESC
        """
        rows = db.execute_query(query)

        inquiries = []
        for row in rows:
            intent_dist = row.get("intent_distribution")
            if isinstance(intent_dist, str):
                intent_dist = json.loads(intent_dist)
            inquiries.append({
                "buyer_nick": row["buyer_nick"],
                "vip_level": row.get("vip_level", "Non-VIP"),
                "dominant_intent": row.get("dominant_intent", "Unknown"),
                "intent_distribution": intent_dist or {},
                "sentiment_label": row.get("sentiment_label", "Neutral"),
                "last_chat_date": str(row["last_chat_date"]) if row.get("last_chat_date") else None,
                "total_chat_messages": row.get("total_chat_messages", 0),
            })

        return {"inquiries": inquiries, "total_count": len(inquiries)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"库存需求查询失败: {str(e)}")
