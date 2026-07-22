# AI Analysis V2 部署与回滚

## 当前安全状态

- `AI_ANALYSIS_V2_PRIORITY_ENABLED` 默认是 `false`，Priority List 继续读取 V1。
- V2 使用独立的五张 shadow tables，不覆盖 `buyer_ai_analysis_cache`。
- 模型失败只记录 run failure，不写事件、客户状态或分析 checkpoint。
- 本文中的生产 DDL、批量生成和 Priority 切换都必须分别获得明确批准。

## 1. 非生产环境验证

先确认数据库目标是隔离的测试库，再创建 V2 表：

```bash
mysql --database smokesignal_v2_test < backend/database/sql/ai_analysis_v2/create_tables.sql
```

后端测试需要分开执行，因为 `tests/ai/conftest.py` 的隔离 stub 不能和 API/database 测试放在同一个 pytest 进程：

```bash
./.venv/bin/python -m pytest -q tests/ai/test_ai_analysis_v2_*.py
./.venv/bin/python -m pytest -q tests/database/test_ai_analysis_v2_repository.py tests/api/test_ai_analysis_v2_routes.py tests/integration/test_ai_analysis_v2_priority.py
./.venv/bin/python -m pytest -q tests/test_failed_analysis_not_cached.py
PATH=/Users/novel/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH npm run build
PATH=/Users/novel/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH npx playwright test tests/frontend/ai-analysis-v2.spec.ts --project=chromium
```

## 2. 50 条金标验收

仅在 V2 表已存在且数据库目标再次确认后写入审核队列：

```bash
./.venv/bin/python scripts/prepare_ai_v2_review_cohort.py --limit 50
./.venv/bin/python scripts/prepare_ai_v2_review_cohort.py --write --limit 50
```

在“AI 问题洞察 → 人工审核”完成 50 条审核后运行：

```bash
./.venv/bin/python scripts/evaluate_ai_v2_gold.py --output docs/testing/ai-analysis-v2-acceptance-report.md
```

只有报告为 `PASS` 才能申请 Priority List 切换。验收要求包括 Negative precision 100%、Negative recall 至少 90%、问题存在一致率至少 90%、问题代码和处理结果一致率至少 80%，并且错误结果落库数和重复事件数都为 0。

## 3. 生产迁移（必须单独批准）

批准前只检查命令，不执行：

```bash
mysql --database dunhill < backend/database/sql/ai_analysis_v2/create_tables.sql
```

迁移后先保持 `AI_ANALYSIS_V2_PRIORITY_ENABLED=false`，生成并审核真实金标。不要在迁移动作中同时切换 Priority List。

## 4. Priority List 切换（必须再次批准）

满足以下条件后，才在运行环境中设置：

```bash
AI_ANALYSIS_V2_PRIORITY_ENABLED=true
```

重启后检查 `/api/v2/priority-customers` 返回 `analysis_version: "v2"`，并确认：

- V2 `urgent/high` 客户进入列表；
- Neutral 客户的真实产品或服务问题保留在趋势中，但不会仅因为有问题就冒充 Negative；
- 已处理客户只有在 `v2.last_event_at > service_updated_at` 时因新事件重新进入；
- 没有 V2 state 的客户继续使用 V1 情感和重评估规则。

## 5. 回滚

先把运行环境切回并重启：

```bash
AI_ANALYSIS_V2_PRIORITY_ENABLED=false
```

确认接口返回 `analysis_version: "v1"` 后即完成业务回滚。V2 shadow tables 默认保留以便调查和恢复；不要自动执行 `drop_tables.sql`。如确需删表，必须作为独立的破坏性操作再次审批。
