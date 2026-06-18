# PriorityList 与异常预警合并 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 删除 Overview 的重复异常入口，将可靠风险信号并入 PriorityList，并让时间对比与月度趋势返回真实、口径正确的数据。

**Architecture:** 风险列表由历史快照、AI 增量情感和客服状态联合生成；期间对比与趋势查询分别使用端点快照和月末快照。所有复杂 SQL 放在 `backend/database/sql/target_buyers/`，分析器通过 `TargetBuyerQueries` 获取数据，前端只消费稳定 v2 契约。

**Tech Stack:** FastAPI, MySQL 8, Python, React 19, TypeScript, Vite, Playwright.

---

### Task 1: 锁定 PriorityList SQL 契约

**Files:**
- Create: `tests/database/test_priority_query_contracts.py`
- Modify: `backend/database/sql/target_buyers/get_priority_customers_count.sql`
- Modify: `backend/database/sql/target_buyers/get_churn_warning.sql`

- [ ] **Step 1: 写失败测试**

测试读取 SQL 文件并断言：count SQL 包含 `customer_service_log` 及与列表一致的重新激活条件；churn SQL 包含增量负面信号、客服状态字段和 `COUNT(*) OVER()`。

- [ ] **Step 2: 验证 RED**

Run: `/Users/novel/Projects/smokesignal-ecommerce-analytics/.venv/bin/python -m pytest tests/database/test_priority_query_contracts.py -q`

Expected: FAIL，因为当前 count SQL 无客服 JOIN，churn SQL 无情感与准确 total。

- [ ] **Step 3: 最小实现**

使 count 默认筛选与列表 SQL 完全一致；重写 churn SQL，加入 `情感转负`、客服状态、处理后重新激活和窗口总数。

- [ ] **Step 4: 验证 GREEN**

Run: `/Users/novel/Projects/smokesignal-ecommerce-analytics/.venv/bin/python -m pytest tests/database/test_priority_query_contracts.py -q`

Expected: PASS。

### Task 2: 修复流失预警 API 分页和类型

**Files:**
- Modify: `backend/api/target_routes.py`
- Modify: `src/api/client.ts`
- Modify: `src/components/dashboard/PriorityAttentionBoard.tsx`
- Test: `tests/api/test_api_endpoints.py`

- [ ] **Step 1: 写失败测试**

增加 API 测试，断言 `/history/churn-warning` 始终返回准确 `total`，每行包含 `service_status`，且 `情感转负` 可作为 selection reason。

- [ ] **Step 2: 验证 RED**

Run: `/Users/novel/Projects/smokesignal-ecommerce-analytics/.venv/bin/python -m pytest tests/api/test_api_endpoints.py -q`

- [ ] **Step 3: 最小实现**

route 从查询行的 `total_count` 提取 total；更新 TypeScript 类型和“流失预警”说明/标签颜色，使客服状态交互使用真实字段。

- [ ] **Step 4: 验证 GREEN**

Run: `/Users/novel/Projects/smokesignal-ecommerce-analytics/.venv/bin/python -m pytest tests/api/test_api_endpoints.py -q`

### Task 3: 实现真实期间对比

**Files:**
- Create: `backend/database/sql/target_buyers/get_period_comparison_metrics.sql`
- Modify: `backend/database/target_buyer_queries.py`
- Modify: `backend/analytics/period_comparator.py`
- Modify: `tests/analytics/test_period_comparator.py`

- [ ] **Step 1: 写失败测试**

用 fake queries 返回两组非零指标，断言比较器正确计算 current、previous、change 和 change_pct；同时测试零基数。

- [ ] **Step 2: 验证 RED**

Run: `/Users/novel/Projects/smokesignal-ecommerce-analytics/.venv/bin/python -m pytest tests/analytics/test_period_comparator.py -q`

- [ ] **Step 3: 最小实现**

新增 SQL，以周期前基线快照和周期末快照计算 new VIC、churn upgrade、VIP upgrade，并按 AI 增量分析时间统计负面沟通。比较器通过可注入 query provider 调用真实查询。

- [ ] **Step 4: 验证 GREEN**

Run: `/Users/novel/Projects/smokesignal-ecommerce-analytics/.venv/bin/python -m pytest tests/analytics/test_period_comparator.py tests/api/test_insights_routes.py -q`

### Task 4: 修复月度趋势重复累计

**Files:**
- Create: `backend/database/sql/target_buyers/get_vic_pool_trend.sql`
- Create: `backend/database/sql/target_buyers/get_vic_active_rate_trend.sql`
- Create: `backend/database/sql/target_buyers/get_high_risk_trend.sql`
- Modify: `backend/database/target_buyer_queries.py`
- Modify: `backend/analytics/trend_aggregator.py`
- Modify: `tests/analytics/test_trend_aggregator.py`

- [ ] **Step 1: 写失败测试**

测试聚合器调用三个 query provider 方法并格式化 Decimal/int；SQL 契约测试断言每个查询先选 `MAX(snapshot_date)` 再聚合。

- [ ] **Step 2: 验证 RED**

Run: `/Users/novel/Projects/smokesignal-ecommerce-analytics/.venv/bin/python -m pytest tests/analytics/test_trend_aggregator.py tests/database/test_priority_query_contracts.py -q`

- [ ] **Step 3: 最小实现**

把内联 SQL 移入三个 SQL 文件，每月只聚合最后一个快照日；TrendAggregator 使用可注入 query provider。

- [ ] **Step 4: 验证 GREEN**

Run: `/Users/novel/Projects/smokesignal-ecommerce-analytics/.venv/bin/python -m pytest tests/analytics/test_trend_aggregator.py tests/api/test_insights_routes.py -q`

### Task 5: 移除前端独立异常入口

**Files:**
- Modify: `src/views/DashboardOverview.tsx`
- Modify: `src/api/insights.ts`
- Modify: `src/types/insights.ts`
- Delete: `src/components/dashboard/AnomalyAlertsCard.tsx`
- Modify: `backend/api/insights_routes.py`
- Modify: `tests/frontend/dashboard-overview.spec.ts`
- Modify: `tests/api/test_insights_routes.py`
- Modify: `tests/integration/test_insights_e2e.py`

- [ ] **Step 1: 写失败测试**

Playwright 断言行动看板不包含“异常客户预警”，仍包含“库存需求”和 PriorityList；API 测试断言旧 anomaly route 的 OpenAPI operation 标记 deprecated。

- [ ] **Step 2: 验证 RED**

Run: `npm run test:e2e -- tests/frontend/dashboard-overview.spec.ts`

- [ ] **Step 3: 最小实现**

移除组件、预取、类型和聚合请求中的 anomaly 字段；后端 route 保留但加 `deprecated=True`。

- [ ] **Step 4: 验证 GREEN**

Run: `npm run test:e2e -- tests/frontend/dashboard-overview.spec.ts`

### Task 6: 真实数据库与浏览器验收

**Files:**
- Modify only if verification exposes a regression.

- [ ] **Step 1: 后端测试**

Run: `/Users/novel/Projects/smokesignal-ecommerce-analytics/.venv/bin/python -m pytest tests/analytics tests/api/test_insights_routes.py tests/api/test_action_routes.py tests/database/test_priority_query_contracts.py -q`

- [ ] **Step 2: 前端构建和 E2E**

Run: `npm run build && npm run test:e2e`

- [ ] **Step 3: 真实 API 验证**

在正确 worktree 后端端口检查 period-comparison、customer-trends、priority-customers、history/churn-warning；确认趋势月值不再是日快照累计，列表 total 与分页一致。

- [ ] **Step 4: 应用内浏览器验证**

刷新 `http://127.0.0.1:4174/`，确认趋势卡片使用真实数据、行动看板无独立异常卡、库存需求和 PriorityList 正常返回。

