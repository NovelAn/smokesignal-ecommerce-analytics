# Overview 改造 — 前端交接文档（Phase 4）

**日期：** 2026-06-14（2026-06-15 验收复核 + 修复）
**状态：** 后端 Phase 2-3 + 前端 Phase 4 均完成。5 模块真实数据验收通过（anomaly 已砍）。Overview 相关 55 测试全过。已修 VIP 升级显示 bug + 宽屏留白。
**前端计划：** 见 `docs/superpowers/plans/2026-06-14-overview-redesign-frontend.md`（15 任务，已实施）

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
  "total_vic_count": int,              // 实测 111
  "key_interests": [                   // ✅ 已聚合为 ~10 个语义主题（非原始词频）
    {"keyword": "成衣偏好", "count": 56, "percentage": 50.5, "examples": ["成衣主导", "梭织外套"]}
  ],
  "key_pain_points": [                 // ✅ 已聚合为 ~9 个主题
    {"keyword": "留存与流失风险", "count": 78, "percentage": 70.3, "examples": ["..."]}
  ],
  "purchase_motivations": [            // 4 个固定 pattern
    {"pattern": "新品尝鲜者", "count": int}   // 复购老客户/新品尝鲜者/价格敏感型/品质追求者
  ],
  "summary": { "headline": "...", "bullets": ["..."] },  // 群体结论
  "raw_label_count": int,              // 原始标签数（313），已归并为主题
  "aggregated_theme_count": int        // 归并后主题数
}
```
**前端现状（2026-06-15 复核）**：已是主题级聚合，`VicPersonaCard` 渲染 Top 8 主题 chip（兴趣/痛点）+ 动机条形 + summary。**无需 Top-N 兜底，质量良好。** 原始词频归并已在 `vic_persona_analyzer._aggregate_themes` 完成。

### 1.2 `GET /api/v2/insights/period-comparison?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
```jsonc
{
  "current_period":  {"start_date": "2026-05-01", "end_date": "2026-05-31"},
  "comparison_period": {"start_date": "2026-03-31", "end_date": "2026-04-30"},  // 自动算等长前期
  "metrics": {
    "new_vic":          {"current": int, "previous": int, "change": int, "change_pct": float | null},
    "churn_warning":    {...同上},
    "vip_upgrades":     {...同上},
    "sentiment_negative": {...同上}
  }
}
```
**状态更新（2026-06-15 复核）：** **3/4 指标真实有效**（非 stub）。实测 30 天窗口（5-14~6-14）：new_vic 9(+28.6%)、churn_warning 31(**+1450% 真实预警信号**，前期仅 2)、vip_upgrades 5。`change_pct` 当 `previous=0` 时返回 **`null`**（前端 `MetricCard` 显示"新增 N"而非误导性的"0.0%"）；`previous=0 & change=0` 也为 null（前端不显示百分比）。`sentiment_negative=0` 是 AI 增量情感覆盖稀疏所致（见 §3），**非 bug**。

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

## 2. 前端验收结果（2026-06-15 真实数据复核）

**5 模块全部通过验收**（anomaly 已按用户决定砍掉，详见 1.3）：

| 模块 | 状态 | 说明 |
|---|---|---|
| VIC 群体画像 | ✅ 完成 | 10 兴趣主题 + 9 痛点主题 + summary，质量良好 |
| 时间对比 | ✅ 3/4 真实 | new_vic/churn/vip 真实；sentiment=0 是数据稀疏非 bug |
| 客户趋势 | ✅ 完成 | 池规模/活跃率/高风险 3 图真实，情感图空态正常 |
| 库存需求 | ✅ 完成 | 21 客户 + 提问原文 + detected_by，纳入逻辑正确 |
| ~~异常预警~~ | 🗑️ 砍掉 | 与 PriorityAttentionBoard 冗余，真实风险走「流失预警」|

**已修复的前端问题（本次 2026-06-15）：**
1. VIP 升级 `previous=0` 时显示 `0.0%` 误导 → 后端返回 `null`，前端显示"新增 N"（`MetricCard.tsx`）
2. 宽屏留白 → `App.tsx` 全局 `max-w-[1600px]` → `max-w-[1920px]`（Overview 组件本身布局正确，留白来自全局限宽居中）

---

## 3. sentiment 数据稀疏（制约 3 处，**非代码 bug**）

2026-06-15 实测 `buyer_ai_analysis_cache`：567 客户中 **428 个(75%) sentiment_label 为 NULL**，仅 131 Neutral / 6 Negative / 2 Positive；`incremental_sentiment_label` 仅 8 条且全在 6/13。**5 月期间 0 条增量情感** → 以下 3 处的 0/空是数据覆盖问题，不是 Overview 代码问题：

1. `period-comparison.sentiment_negative=0`（周期内无增量负面记录）
2. ~~`anomaly-alerts.sentiment_negative`~~（模块已砍）
3. `customer-trends.sentiment_trend=[]`（history 表无情感字段，前端已做空态提示）

**根因**：AI 情感分析覆盖度不足。根治需给更多客户跑 sentiment（成本 + 时间，且月度趋势需按月持续跑），属独立的数据工程，不在 Overview 范围。用户已选择**接受现状如实标注**（前端不造假，随 AI 日常分析自然积累）。

---

## 4. 仍挂起的后端项（不阻塞前端）

1. Inventory Inquiry 的 AI 回填（Task 1 prompt 上线后自然积累，1-2 周；当前 21 条全 keyword 来源）
2. Task 2 库存 intent 准确率测试待用户手动执行（花 ¥，需 API keys）
3. ~~vic-persona 聚合优化~~ ✅ 已完成（主题归并）
4. ~~period 真实环比~~ ✅ 已完成（3/4 真实）
5. ~~沟通频率骤降~~ 随 anomaly 模块砍掉，不再需要

---

## 5. 复现 / 验证命令

```bash
cd /Users/novel/Projects/smokesignal-ecommerce-analytics/.claude/worktrees/feature+overview-redesign
# 后端（reload 模式，改后端代码自动重载）
API_RELOAD=true /Users/novel/Projects/smokesignal-ecommerce-analytics/.venv/bin/python -m backend.main &
# 前端（端口冲突时会自动换，如 3001）
npm run dev
# 验证 period 返回 null（VIP previous=0）
curl -s "http://localhost:8000/api/v2/insights/period-comparison?start_date=2026-05-14&end_date=2026-06-14" | python -m json.tool
# 后端测试（避开顶层改 stdio 的旧脚本）
/Users/novel/Projects/smokesignal-ecommerce-analytics/.venv/bin/python -m pytest tests/analytics/ tests/api/test_action_routes.py tests/api/test_insights_routes.py tests/integration/test_insights_e2e.py -q
```
