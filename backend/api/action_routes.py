"""Action API routes — customer demand action endpoints.

v2 routes surfacing actionable customer segments. Currently exposes
inventory-inquiry buyers so ops can act on stock / restock demand.
"""
import json
from collections import OrderedDict

from fastapi import APIRouter, HTTPException

from backend.database import Database
from backend.analytics.keyword_categories import KEYWORD_CATEGORIES

router = APIRouter(prefix="/api/v2/action", tags=["action"])

# 复用关键词词典里的「库存查询」词表（单一事实来源）——仅作兜底 + 取提问原文
_INVENTORY_KEYWORDS = KEYWORD_CATEGORIES.get("库存查询", [])


@router.get("/inventory-inquiries")
async def get_inventory_inquiries():
    """库存需求客户列表（AI 主路径，关键词兜底）。

    纳入标准（取并集）：
      - AI 主：buyer_ai_analysis_cache.intent_distribution 中 Inventory Inquiry 占比 > 0。
        关键点：**不要求是 dominant_intent**——某客户可能售前咨询条数最多（被打成售前），
        但只要 distribution 里存在库存意图（任何占比），就纳入。
      - 关键词兜底：chat_history 中买家发送的消息命中库存关键词。
        覆盖尚未被 AI 分析的客户（当前 0 客户有 AI 库存意图，此路径先行提供数据）。

    每条返回：
      - buyer_nick / vip_level
      - inventory_questions：最近 3 条库存相关提问原文（截断 120 字，来自 chat_history 关键词命中）
      - question_count：库存相关提问总数
      - last_inventory_msg_time：最近一次库存提问时间
      - last_chat_date / dominant_intent / intent_distribution / sentiment_label：AI 增强
      - detected_by："ai" | "keyword" | "both"（来源：AI 检测 / 关键词兜底 / 两者）

    排序：按库存需求发出日期（last_inventory_msg_time）降序——最近的需求排最前。
    原因：客户最后聊天起算超 2 周即无法主动旺旺触达，最近发出需求的最可能仍在触达窗口。
    """
    try:
        db = Database()

        # ---- Set A: AI 检测到库存意图的客户（占比 > 0，不限 dominant）----
        ai_rows = db.execute_query(
            """
            SELECT buyer_nick, dominant_intent, intent_distribution, sentiment_label
            FROM buyer_ai_analysis_cache
            WHERE JSON_EXTRACT(intent_distribution, '$."Inventory Inquiry"') > 0
            """
        )
        ai_map = {r["buyer_nick"]: r for r in ai_rows}

        # ---- Set B: 关键词命中（兜底纳入 + 取提问原文）----
        grouped: "OrderedDict[str, dict]" = OrderedDict()
        detected_by: dict = {}
        if _INVENTORY_KEYWORDS:
            like_clauses = " OR ".join(["content LIKE %s" for _ in _INVENTORY_KEYWORDS])
            like_params = [f"%{kw}%" for kw in _INVENTORY_KEYWORDS]
            msg_rows = db.execute_query(
                f"""
                SELECT user_nick AS buyer_nick, content, msg_time
                FROM chat_history
                WHERE sender_nick = user_nick
                  AND ({like_clauses})
                ORDER BY user_nick, msg_time DESC
                """,
                like_params,
            )
            for r in msg_rows:
                buyer = r["buyer_nick"]
                if buyer not in grouped:
                    grouped[buyer] = {
                        "buyer_nick": buyer,
                        "inventory_questions": [],
                        "question_count": 0,
                        "last_inventory_msg_time": r["msg_time"],
                    }
                grouped[buyer]["question_count"] += 1
                if len(grouped[buyer]["inventory_questions"]) < 3:
                    text = (r.get("content") or "").strip()
                    if text:
                        grouped[buyer]["inventory_questions"].append(text[:120])
                detected_by[buyer] = "keyword"

        # ---- 合并：AI 集合里、关键词未命中的客户也纳入（提问原文为空）----
        for buyer, ai_row in ai_map.items():
            if buyer not in grouped:
                grouped[buyer] = {
                    "buyer_nick": buyer,
                    "inventory_questions": [],
                    "question_count": 0,
                    "last_inventory_msg_time": None,
                }
            detected_by[buyer] = "both" if detected_by.get(buyer) == "keyword" else "ai"

        if not grouped:
            return {"inquiries": [], "total_count": 0}

        # ---- 增强：VIP / 最近聊天 / AI 意图情感（来自 precomputed + ai cache）----
        buyer_nicks = list(grouped.keys())
        placeholders = ",".join(["%s"] * len(buyer_nicks))
        enrich_rows = db.execute_query(
            f"""
            SELECT tb.buyer_nick, tb.vip_level, tb.last_chat_date,
                   ai.dominant_intent, ai.intent_distribution, ai.sentiment_label,
                   ai.updated_at AS ai_updated_at,
                   csl.status AS service_status,
                   csl.notes AS service_notes,
                   csl.updated_at AS service_updated_at
            FROM target_buyers_precomputed tb
            LEFT JOIN buyer_ai_analysis_cache ai ON tb.buyer_nick = ai.buyer_nick
            LEFT JOIN customer_service_log csl
              ON tb.buyer_nick = csl.buyer_nick
             AND csl.workstream = 'inventory'
            WHERE tb.buyer_nick IN ({placeholders})
            """,
            buyer_nicks,
        )
        enrich_map = {e["buyer_nick"]: e for e in enrich_rows}

        inquiries = []
        for buyer, info in grouped.items():
            e = enrich_map.get(buyer, {})
            ai_row = ai_map.get(buyer, {})
            service_status = e.get("service_status") or "pending"
            service_updated_at = e.get("service_updated_at")
            latest_inventory_event = info.get("last_inventory_msg_time") or e.get("ai_updated_at")
            if (
                service_status in {"contacted", "resolved"}
                and service_updated_at
                and (not latest_inventory_event or latest_inventory_event <= service_updated_at)
            ):
                continue
            # 优先用 ai_set 的意图数据，否则用 enrich（两者同源，取非空）
            intent_dist = ai_row.get("intent_distribution") or e.get("intent_distribution")
            if isinstance(intent_dist, str):
                intent_dist = json.loads(intent_dist)
            inquiries.append({
                "buyer_nick": buyer,
                "vip_level": e.get("vip_level") or "Non-VIP",
                "inventory_questions": info["inventory_questions"],
                "question_count": info["question_count"],
                "last_inventory_msg_time": str(info["last_inventory_msg_time"]) if info["last_inventory_msg_time"] else None,
                "last_chat_date": str(e["last_chat_date"]) if e.get("last_chat_date") else None,
                "dominant_intent": (ai_row.get("dominant_intent") or e.get("dominant_intent")) or "Unknown",
                "intent_distribution": intent_dist or {},
                "sentiment_label": (ai_row.get("sentiment_label") or e.get("sentiment_label")) or "Unknown",
                "detected_by": detected_by.get(buyer, "keyword"),
                "service_status": service_status,
                "service_notes": e.get("service_notes") or "",
                "service_updated_at": str(service_updated_at) if service_updated_at else None,
            })

        # 排序：纯按库存需求发出日期（last_inventory_msg_time）降序。
        # 业务原因：客户最后聊天起算超过 2 周即无法主动旺旺触达，最近发出需求的客户
        # 最可能仍在触达窗口内，应优先处理 → 最新日期排最前。无提问时间的（AI-only）排末尾。
        inquiries.sort(key=lambda x: x["last_inventory_msg_time"] or "", reverse=True)

        return {"inquiries": inquiries, "total_count": len(inquiries)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"库存需求查询失败: {str(e)}")
