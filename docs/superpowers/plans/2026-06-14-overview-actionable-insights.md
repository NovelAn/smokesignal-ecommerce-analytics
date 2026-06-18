# Overview 可行动洞察 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 VIC 原始标签归并为群体结论，为库存需求加入独立客服处理闭环，并让关键词与顶部指标明确使用真实数据库口径。

**Architecture:** VIC 使用确定性主题分类器；客服日志通过 workstream 隔离任务队列；关键词按时间范围实时读取 chat_history；顶部指标保留当前快照语义并暴露更新时间。

**Tech Stack:** FastAPI, MySQL 8, Python, React 19, TypeScript, Vite, Playwright.

---

### Task 1: VIC 主题归并

**Files:** backend/analytics/vic_persona_analyzer.py, tests/analytics/test_vic_persona_analyzer.py, src/types/insights.ts, src/components/dashboard/VicPersonaCard.tsx

- [ ] 写失败测试：同一客户的“成衣主导”和“梭织外套”只贡献一次“成衣偏好”，并生成 summary。
- [ ] 运行 VIC 单元测试，确认因主题归并不存在而失败。
- [ ] 实现主题词典、单客户去重、examples 和 summary。
- [ ] 更新前端只展示聚合主题、总结和归并数量。
- [ ] 重跑测试。

### Task 2: 客服 workstream 迁移

**Files:** backend/database/sql/add_customer_service_workstream.sql, backend/database/sql/create_customer_service_log.sql, tests/database/test_service_workstream_contract.py

- [ ] 写失败 SQL 契约测试，要求 workstream、复合唯一键和非破坏 UPDATE。
- [ ] 运行测试确认失败。
- [ ] 编写幂等迁移脚本和新环境建表结构。
- [ ] 运行 SQL 契约测试。

### Task 3: 通用客服状态 API

**Files:** backend/database/target_buyer_queries.py, backend/analytics/target_buyer_analyzer.py, backend/api/target_routes.py, src/api/client.ts, tests/api/test_api_endpoints.py

- [ ] 写失败测试，断言 mark 接受 inventory workstream 且默认仍为 priority。
- [ ] 运行测试确认失败。
- [ ] 让 mark、batch mark 和 history 按 workstream 读写。
- [ ] 重跑 API 测试。

### Task 4: 库存队列处理状态

**Files:** backend/database/sql/target_buyers/get_inventory_inquiries.sql, backend/api/action_routes.py, src/types/insights.ts, src/components/dashboard/InventoryInquiriesCard.tsx, tests/api/test_action_routes.py, tests/frontend/dashboard-overview.spec.ts

- [ ] 写失败测试，覆盖 resolved 后隐藏、新库存提问后重新出现和 service_status 返回。
- [ ] 运行后端与 Playwright 测试确认失败。
- [ ] 将库存候选查询与状态过滤放入 SQL，前端复用状态按钮并在操作后刷新。
- [ ] 重跑测试。

### Task 5: 实时关键词分析

**Files:** backend/analytics/keyword_analyzer.py, backend/database/sql/target_buyers/get_keyword_messages.sql, backend/api/target_routes.py, src/api/client.ts, src/components/dashboard/KeywordAnalysisPanel.tsx, tests/analytics/test_keyword_analyzer.py

- [ ] 写失败测试，覆盖日期过滤后的消息分类和统一消息计数口径。
- [ ] 运行测试确认失败。
- [ ] 实现实时消息查询和纯 Python 聚合器。
- [ ] 前端从 TimeRangeContext 传日期，并显示 live 数据范围及最后消息时间。
- [ ] 重跑后端和前端测试。

### Task 6: 顶部快照透明度

**Files:** backend/database/sql/target_buyers/get_dashboard_metrics.sql, src/components/dashboard/MetricCards.tsx, src/components/common/TimeRangeFilter.tsx, tests/database/test_priority_query_contracts.py, tests/frontend/dashboard-overview.spec.ts

- [ ] 写失败测试，要求最新 AI 情感优先及页面显示快照更新时间。
- [ ] 运行测试确认失败。
- [ ] 更新 SQL 和卡片说明；时间筛选改名。
- [ ] 重跑测试。

### Task 7: 迁移与完整验收

- [ ] 在真实数据库执行迁移，前后核对行数。
- [ ] 运行相关 Python 测试、完整前端 build 和 Playwright。
- [ ] 启动 worktree 后端和前端，检查真实 API 数量与时间戳。
- [ ] 用应用内浏览器确认全部交互。

