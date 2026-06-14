# PriorityList 与异常预警合并设计

**日期：** 2026-06-14

## 目标

将独立的“异常客户预警”收敛到 `PriorityAttentionBoard`，让所有需要客服跟进的客户共用同一套筛选、分页、处理状态和重新激活逻辑。同时修复 Overview 新组件中已经确认的真实数据问题。

## 产品边界

- 前端不再展示独立的 `AnomalyAlertsCard`，也不再主动请求 `/api/v2/insights/anomaly-alerts`。
- `/api/v2/insights/anomaly-alerts` 暂时保留并标记 deprecated，避免潜在调用方立即中断；其旧实现不再作为 Overview 的产品逻辑。
- `PriorityAttentionBoard` 的“流失预警”成为统一风险入口，保留现有三类可靠信号：segment 退化、churn risk 升级、L6M 购买力坍塌。
- 新增可靠的“情感转负”信号：只使用 `buyer_ai_analysis_cache.incremental_sentiment_label = 'Negative'` 且分析时间落在所选窗口内的数据。
- “超过 180 天未购买”不再单独定义为异常。
- “沟通频率骤降”本轮不做。历史快照缺少可比聊天字段，后续补齐数据基础后单独设计和迁移。

## PriorityList 数据流

`GET /api/v2/history/churn-warning` 从历史快照、当前预计算表、AI 增量分析和客服处理记录生成统一列表：

1. 用窗口前快照与最新快照计算 segment、churn risk、L6M 变化。
2. 用 AI 增量分析识别窗口内真实负面沟通。
3. 至少命中一个信号才入选。
4. 未处理或 pending 客户正常显示。
5. contacted/resolved 客户只在处理后发生新风险信号时重新进入列表。
6. SQL 使用窗口总数返回准确分页 total，并返回客服状态字段供现有交互复用。

`GET /api/v2/priority-customers` 的 count SQL 必须与列表 SQL 使用完全相同的客服状态与重新激活条件，消除列表数量和 total 不一致。

## Overview 真实数据修复

### 时间对比

`period-comparison` 不再返回固定零值。每个时间段选择“开始日前最近快照”作为基线、“结束日及以前最近快照”作为期末，计算：

- `new_vic`：期末为 VIC/BOTH，基线不存在或不是 VIC/BOTH。
- `churn_warning`：基线 churn risk 为低/中，期末为高。
- `vip_upgrades`：期末 VIP 等级高于基线。
- `sentiment_negative`：AI 增量负面分析时间落在该周期内的客户数。

如果请求日期没有覆盖到任何期末快照，指标返回 0；不伪造数据。

### 客户趋势

每个月只使用该月最后一个快照日计算客户池、活跃率和高风险数量，避免把每日快照重复相加。情感趋势仍保持明确空态，因为历史表没有情感字段。

## 错误与兼容处理

- 保持现有 v2 URL 和前端类型的主要字段不变。
- deprecated 异常接口继续返回原契约，OpenAPI 中明确标记废弃。
- SQL 查询放在 `backend/database/sql/target_buyers/`，Python 不新增复杂内联 SQL。
- 不修改数据库结构、凭据、环境变量文件或生产数据。

## 验证

- 单元测试覆盖期间快照选择、真实指标变化、月末快照聚合和空数据。
- SQL/查询测试覆盖 priority count 与列表相同默认条件、流失预警的负面信号、客服状态及 total。
- API 测试覆盖 deprecated 标记后的兼容响应和 churn-warning total。
- Playwright 覆盖行动看板不再出现独立异常卡片、仍展示库存需求和 PriorityList。
- 使用正确 worktree 后端连接真实数据库，确认 period-comparison 不再是固定 stub、趋势数量处于客户规模而非每日快照累计规模。

