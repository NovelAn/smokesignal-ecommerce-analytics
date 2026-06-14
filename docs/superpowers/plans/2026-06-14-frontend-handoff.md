# Overview 改造 — 前端交接文档（Phase 4）

**日期：** 2026-06-14
**后端状态：** Phase 2-3 完成（11/11 任务 + 库存纳入逻辑修正），40 测试全过，5 个新 API 已对真实 DB 验证
**前端计划：** 见 `docs/superpowers/plans/2026-06-14-overview-redesign-frontend.md`（15 个任务）

> ⚠️ **本文档的 API 契约是真实跑出来的，优先级高于前端计划里的假设。** 前端计划写于后端实现前，部分响应结构已变化（尤其库存端点）。以下为准。

---

## 0. 环境约定（必读）

- **跑前端用** `npm run dev`（前端环境独立，无问题）
- **跑后端/测试用主仓 `.venv`**：`/Users/novel/Projects/smokesignal-ecommerce-analytics/.venv/bin/python`（worktree 自己的 venv 缺 fastapi/openai，不能用）
- **DB 从本机直连可通**（aliyunDB，530 个 target buyers）。MCP 的 mysql 工具在此环境不可用（IP 白名单），别用它
- schema 踩坑记录见记忆文件 `smokesignal-db-schema-gotchas`（persona_* 列名前缀、churn_risk='高'、chat_history.user_nick、BOTH 保留字等）

---

## 1. 已交付的 API（2026-06-14 后端复核）

### 1.1 `GET /api/v2/insights/vic-persona`
```jsonc
{
  "total_vic_count": int,              // 当前 ~116
  "key_interests": [                   // ⚠️ 当前 313 条，未去重/未 TF-IDF，含 AI 生成的长句
    {"keyword": "高频复购", "count": int, "percentage": float}
  ],
  "key_pain_points": [                 // ⚠️ 当前 212 条，同上
    {"keyword": "...", "count": int, "percentage": float}
  ],
  "purchase_motivations": [            // 4 个固定 pattern
    {"pattern": "新品尝鲜者", "count": int}   // 复购老客户/新品尝鲜者/价格敏感型/品质追求者
  ]
}
```
**前端建议**：兴趣/痛点只展示 Top N（如 15-20），按 count 降序；可加"展开更多"。
**已知限制**：聚合是原始词频，未做显著性/去重，长句较多。属后端待优化项（TF-IDF/聚类），前端先 Top-N 兜底。

### 1.2 `GET /api/v2/insights/period-comparison?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
```jsonc
{
  "current_period":  {"start_date": "2026-05-01", "end_date": "2026-05-31"},
  "comparison_period": {"start_date": "2026-03-31", "end_date": "2026-04-30"},  // 自动算等长前期
  "metrics": {
    "new_vic":          {"current": int, "previous": int, "change": int, "change_pct": float},
    "churn_warning":    {...同上},
    "vip_upgrades":     {...同上},
    "sentiment_negative": {...同上}
  }
}
```
**状态更新（2026-06-14）：** 已接入真实历史快照首尾对比，不再返回固定 0。情感转负使用 AI 增量分析时间统计；如果周期内没有真实增量负面记录，该项为 0。

### 1.3 `GET /api/v2/insights/anomaly-alerts`（deprecated）
```jsonc
{
  "anomalies": [              // 最多 50 条
    {
      "buyer_nick": "...",
      "vip_level": "V3|V2|V1|V0|Non-VIP",
      "anomaly_type": "sentiment_negative|purchase_interval_long|chat_frequency_drop",
      "anomaly_reason": "距上次购买 214 天，超过 180 天",
      "last_purchase_date": "2025-11-12 22:37:18",   // ⚠️ 完整 datetime 字符串
      "last_chat_date": "2025-11-14 18:27:42",
      "severity": "high|medium"
    }
  ],
  "total_count": int          // 实际总数（可能 > 50）
}
```
**状态更新（2026-06-14）：** 独立异常卡已从 Overview 移除，真实风险信号统一进入 `PriorityAttentionBoard → 流失预警`。此接口仅为兼容保留，并在 OpenAPI 标记 deprecated。

### 1.4 `GET /api/v2/insights/customer-trends?months=N`（默认 6，范围 1-24）
```jsonc
{
  "vic_pool_trend": [         // 堆叠面积图：SMOKER/VIC/BOTH
    {"month": "2025-12", "SMOKER": int, "VIC": int, "BOTH": int}
  ],
  "vic_active_rate_trend": [  // 折线图
    {"month": "2025-12", "total_vic": int, "active_vic": int, "active_rate": float}
  ],
  "high_risk_trend": [        // 折线图
    {"month": "2025-12", "high_risk_count": int}
  ],
  "sentiment_trend": []       // ⚠️ 恒为空，history 表无情感字段
}
```
**状态更新（2026-06-14）：** 客户池、活跃率和高风险趋势改为每月最后一个快照日，已修复按日快照重复累计问题。`sentiment_trend` 仍为空（历史表无情感字段）；`active_rate` 基于“当月有购买”。

### 1.5 `GET /api/v2/action/inventory-inquiries` ⭐（结构已变更，与前端计划不同）
```jsonc
{
  "inquiries": [
    {
      "buyer_nick": "无法平复的悲伤",
      "vip_level": "V1",
      "inventory_questions": [         // ⭐ 新增：最近 3 条库存提问原文（截断 120 字）
        "你好 我当时想拍这个的时候这个41没货了 但是我现在看又有货了..."
      ],
      "question_count": int,            // ⭐ 库存相关提问总数
      "last_inventory_msg_time": "2026-05-19 21:24:38",  // ⭐ 最近库存提问
      "last_chat_date": "2026-06-01 18:40:26",
      "dominant_intent": "Post-sale Support",   // 注意：可能不是 Inventory Inquiry
      "intent_distribution": {                  // ⚠️ 可能是计数(int)或占比(float)，且可能无 Inventory Inquiry 键
        "Pre-sale Inquiry": int, "Post-sale Support": int, ...
      },
      "sentiment_label": "Neutral|Positive|Negative|Unknown",
      "detected_by": "ai|keyword|both"          // ⭐ 来源标记
    }
  ],
  "total_count": int            // 当前 21（关键词兜底）
}
```

**库存组件的核心业务逻辑（用户明确要求）：**
- 纳入标准 = `intent_distribution['Inventory Inquiry'] > 0`（**任何**库存意图，不要求是 dominant）**∪** 关键词兜底（chat_history 命中库存词）
- 关键点：**一个客户可能 dominant_intent 是售前/售后，但仍被列入**（只要他问过库存）。前端不要假设 `dominant_intent==='Inventory Inquiry'` 才显示
- `detected_by`：`ai`=AI 检测到库存意图、`keyword`=关键词兜底、`both`=两者。可用来区分置信度（ai/both 更可信）
- **当前 21 条全部是 keyword 来源**（AI 库存意图尚未回填，0 客户）。随 Task 1 的 prompt 上线、新对话被分析后，`ai`/`both` 会逐步出现

---

## 2. 前端计划需调整的点

| 前端计划任务 | 调整 |
|---|---|
| Task 6 (InventoryInquiries 组件) | 字段已变（见 1.5）。必须渲染 `inventory_questions`（提问原文，最有行动价值）、`detected_by` 标签、`question_count`。**不要**按 `dominant_intent==='Inventory Inquiry'` 过滤 |
| VIC 群体画像 | key_interests/key_pain_points 数量很多（200-300），需 Top-N + 展开 |
| 时间对比卡片 | 数字当前是 0（stub），按结构渲染即可，后端补数据后生效 |
| 趋势图 sentiment | sentiment_trend 恒空，图表需做空态处理 |

---

## 3. 已知后端待办（不影响前端开发，前端按现状渲染即可）

1. `vic-persona` 兴趣/痛点聚合优化（TF-IDF/去重，当前原始词频）
2. `customer-trends.sentiment_trend` 数据源（history 无情感字段）
3. 沟通频率骤降（需先为历史快照补齐可比较聊天字段）
4. Inventory Inquiry 的 AI 回填（Task 1 prompt 上线后自然积累，1-2 周）
5. Task 2 库存 intent 准确率测试待用户手动执行（花 ¥，需 API keys）

---

## 4. 启动新会话的第一步

```bash
cd /Users/novel/Projects/smokesignal-ecommerce-analytics/.claude/worktrees/feature+overview-redesign
# 读两份文档：
#   docs/superpowers/plans/2026-06-14-overview-redesign-frontend.md  （15 任务主体）
#   docs/superpowers/plans/2026-06-14-frontend-handoff.md            （本文档，API 真实契约）
# 验证后端在跑：
/Users/novel/Projects/smokesignal-ecommerce-analytics/.venv/bin/python -m backend.main &
curl -s http://localhost:8000/api/v2/action/inventory-inquiries | python -m json.tool | head
```
