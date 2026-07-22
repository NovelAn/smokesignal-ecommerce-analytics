# AI Analysis V2 设计规范

> 日期：2026-07-22
>
> 状态：用户已确认（2026-07-22）
>
> 适用项目：SmokeSignal Analytics
>
> 目标：把现有“客户级情感 + 粗粒度意图”升级为可增量、可审核、可聚合的“事件 + 多问题 + 当前状态”分析闭环。

## 1. 当前状态与缺口

当前系统已经具备：

- `buyer_ai_analysis_cache` 中的客户级情感、意图和画像缓存。
- MiniMax 优先、DeepSeek 备用的模型调用链。
- 模型失败不写缓存、不推进分析快照的可重试保障。
- 基于完整客服对话、严格限制 Negative 的情感判断。
- Negative 客户进入现有 Priority List 的运营逻辑。
- AI Analysis V2 人工审核工作台静态原型。

当前系统尚不具备：

- 一段对话中识别多个具体问题。
- 问题类型、问题详情、严重度、责任归属、处理结果和证据的结构化数据。
- 不覆盖历史的事件记录和只分析新增聊天的增量链路。
- 从历史事件汇总出的客户“当前状态”。
- 跨客户的产品、物流、售后和客服问题趋势。
- 50 个分层案例的人工审核、修正和金标准数据集。
- V2 的正式 API、客户详情展示、趋势页面和审核页面。

因此，提交 `3e55bbd` 只完成了 V2 的情感语义前置修复，不代表 AI Analysis V2 已完成。

## 2. 已确认的业务目标

AI Analysis V2 必须同时回答两类不同问题：

1. **这个客户现在是否需要优先处理？**
   - 当前情感是否 Negative。
   - 是否存在未解决的高严重度问题。
   - 客服是否已经解释、客户是否接受。
   - 下一步应该采取什么动作。

2. **众多客户正在共同反映什么问题？**
   - 哪类产品、物流、价格、售后或客服问题在增加。
   - 有多少不同客户受到影响。
   - 问题是否未解决、是否反复出现。
   - 问题趋势不能依赖客户是否达到 Negative。

Negative 仍然会直接提高客户关注优先级，但 Neutral 客户反映的真实产品和服务问题也必须进入问题趋势。

## 3. 方案比较与选择

### 方案 A：继续扩展 `buyer_ai_analysis_cache`

在现有“一客户一行”缓存中继续增加 JSON 字段。

- 优点：改动少。
- 缺点：无法可靠保存多个历史事件、多个问题和审核版本；SQL 趋势聚合困难；增量更新容易覆盖历史。
- 结论：不采用。

### 方案 B：V2 影子表 + 规范化事件和问题（采用）

保留 V1 缓存，新增独立的 V2 run、event、issue、customer state 和 review 表。

- 优点：不破坏现有系统；历史、当前状态和问题趋势职责清楚；审核通过前可以影子运行。
- 缺点：需要新增数据库表和独立 API。
- 结论：采用。它是满足完整闭环的最小可靠结构。

### 方案 C：每个客户保存一份完整 JSON 文档

- 优点：模型输出可以直接保存。
- 缺点：跨客户趋势、问题状态更新、去重、审核修正和索引查询都不稳定。
- 结论：不采用。

## 4. 总体架构

```text
chat_history
    │
    ├─ 程序：读取新增消息、排序、脱敏、明显会话分段、生成指纹
    │
    ├─ MiniMax：语义判断事件、情感、多问题、处理结果和建议动作
    │      └─ schema 失败重试一次
    │
    ├─ DeepSeek：仅在 MiniMax 重试失败且客户属于高价值/高风险时使用
    │
    ├─ 严格 schema 校验
    │      ├─ 失败：只记录 run failure，不写事件/问题/状态，不推进 checkpoint
    │      └─ 成功：单事务写入 event + issues + customer_state
    │
    ├─ 单客户：当前状态、问题历史、关注优先级
    ├─ 跨客户：问题趋势、影响客户数、未解决数量
    └─ 人工审核：50 个分层案例 → 修正 → 金标准
```

运行时不使用 sub-agent。程序只负责确定性机械工作；情感、问题语义、问题详情、处理结果和模糊话题边界由模型判断。

## 5. 模型与程序职责边界

### 5.1 程序负责

- 查询聊天记录并按时间排序。
- 只取新增消息并附带有限历史上下文。
- 过滤空消息、图片 URL、纯系统快捷消息。
- 对手机号、订单号、物流单号等明显标识符脱敏。
- 按 24 小时时间间隔进行明显会话预分段。
- 生成消息窗口指纹，保证重复执行幂等。
- 校验模型 JSON schema 和枚举值。
- 持久化、事务、重试状态和 checkpoint。
- 计算历史衰减权重、客户当前状态和趋势聚合。

### 5.2 模型负责

- 模糊情况下判断新话题还是旧问题延续。
- 判断事件整体情感和峰值情绪。
- 从同一事件中识别零个、一个或多个问题。
- 判断问题类型、详情、严重度、责任归属和证据。
- 判断客服是否解释、客户是否接受、问题是否解决。
- 给出可执行的下一步建议。

### 5.3 禁止事项

- 不使用单一关键词决定情感、Complaint、问题类型或处理结果。
- 不使用规则引擎生成语义结果作为模型失败后的成功缓存。
- 不把模型错误、超时、截断文本或占位符保存为 V2 分析结果。
- 不把客服道歉本身当成客户 Negative 的证据。

## 6. 事件和问题定义

### 6.1 事件 Event

事件是一段围绕同一业务主题的连续客服交互。明显跨越 24 小时的聊天由程序预分段；24 小时内是否属于同一主题由模型判断。

事件字段：

- `topic_summary`：一句话主题摘要。
- `event_started_at` / `event_ended_at`：事件时间范围。
- `sentiment_label`：`Positive | Neutral | Negative`。
- `sentiment_score`：0 到 1。
- `sentiment_basis`：与严格情感标准一致的依据类型。
- `peak_emotion`：`calm | concern | anxiety | dissatisfaction | anger | gratitude`。
- `service_friction`：`none | low | medium | high`。
- `resolution_status`：`unresolved | explained_pending_acceptance | resolved | unknown`。
- `customer_accepted`：`true | false | null`。
- `suggested_action`：下一步动作。

情感与问题严重度相互独立。客户可以是 Neutral，同时存在真实产品问题或未解决问题。

### 6.2 问题 Issue

同一个事件允许零个或多个问题。每个问题包含：

- `issue_category`：一级归属。
- `issue_code`：可聚合的稳定二级编码。
- `issue_detail`：结合本次语境的具体描述。
- `severity`：`low | medium | high | critical`。
- `owner`：`product | logistics | service | customer | mixed | unknown`。
- `status`：`open | explained_pending_acceptance | resolved | unknown`。
- `is_primary`：是否为该事件主问题。
- `evidence_text`：经过脱敏的买家原话。
- `evidence_msg_time`：证据时间。

### 6.3 V2 首版问题分类

| 一级分类 | `issue_code` |
|---|---|
| product | `material_expectation`, `color_appearance_mismatch`, `size_fit`, `quality_damage`, `packaging` |
| logistics | `shipping_delay`, `delivery_failure`, `return_pickup`, `address_contact` |
| after_sales | `return_request`, `exchange_request`, `refund_delay`, `repair_warranty` |
| pricing_promotion | `price_change`, `discount_eligibility`, `price_difference` |
| inventory | `out_of_stock`, `replenishment_wait` |
| service | `response_slow`, `explanation_unclear`, `repeated_communication`, `service_attitude` |
| trust | `authenticity_concern`, `advertising_mismatch` |
| usage_care | `usage_instruction`, `care_maintenance` |
| other | `other` |

模型必须从以上编码中选择；具体事实写入 `issue_detail`，不得为了新措辞临时创造编码。

## 7. 增量分析与历史保留

### 7.1 首次分析

- 读取最近 50 条聊天。
- 程序按明显时间边界生成候选窗口。
- 模型可以在窗口内输出多个事件和每个事件的多个问题。
- 成功后把 `customer_state.analyzed_through_msg_time` 更新为本次最新消息时间。

### 7.2 增量分析

- 只读取 checkpoint 之后的新消息。
- 附带最多 20 条旧消息，以及最近 3 个未解决事件摘要作为语境。
- 模型返回 `new_event` 或 `continue_event`。
- `continue_event` 只能引用输入中提供的事件 ID；程序不允许模型任意生成 ID。
- 旧事件不删除。延续事件可以更新其解决状态和最后活动时间；成功 run 的脱敏 `result_payload` 保留每次变化前后的模型输出。
- 成功才推进 checkpoint；失败后下次仍分析同一批新增消息。

### 7.3 幂等

- 消息窗口生成 SHA-256 `source_fingerprint`。
- run 额外包含可空的 `completed_fingerprint`；只有成功事务才把它设为 `source_fingerprint`。
- `(buyer_nick, completed_fingerprint, prompt_version)` 唯一。MySQL 允许多个 NULL，因此失败 run 可以保留并继续重试，成功输入不会重复写入。
- 相同输入重复执行返回已有成功 run，不重复创建事件和问题。
- 失败 run 不占用成功唯一键，可以重试。

## 8. 历史衰减与客户当前状态

历史事件永久保留，但当前状态优先反映新问题。

每个问题的当前权重：

```text
severity_factor:
  low=1, medium=2, high=3, critical=4

status_factor:
  open=1.0
  explained_pending_acceptance=0.7
  unknown=0.5
  resolved=0.15

recency_factor:
  0-30天=1.0
  31-90天=0.6
  91-180天=0.3
  180天以上=0.1

issue_weight = severity_factor × status_factor × recency_factor
```

客户当前状态规则：

- `primary_issue`：权重最高的问题；并列时取最近问题。
- `active_issue_count`：状态不是 `resolved` 的问题数量。
- `current_sentiment`：最近 90 天最新事件的情感；无事件则为 `Unknown`。
- `attention_priority`：独立于现有销售 `follow_priority`。
  - `urgent`：最近 Negative 且存在 critical/high 未解决问题。
  - `high`：最近 Negative，或存在 high/critical 未解决问题。
  - `medium`：存在 medium 未解决问题，或 `service_friction=high`。
  - `low`：其他情况。
- `recommended_action`：最近未解决主问题对应的模型建议。

现有 Priority List 使用“销售优先级 OR V2 attention priority”。V2 Negative 至少进入 `high`，不会降低原销售优先级。

## 9. 数据库设计

V2 使用 5 张影子表，不修改 `buyer_ai_analysis_cache` 的历史结构。

### 9.1 `ai_analysis_v2_runs`

- `id BIGINT PRIMARY KEY AUTO_INCREMENT`
- `buyer_nick VARCHAR(255) NOT NULL`
- `analysis_mode ENUM('full','incremental') NOT NULL`
- `status ENUM('running','completed','failed') NOT NULL`
- `provider VARCHAR(32)` / `model VARCHAR(64)` / `prompt_version VARCHAR(32)`
- `source_fingerprint CHAR(64) NOT NULL`
- `completed_fingerprint CHAR(64) NULL`
- `source_from_msg_time DATETIME` / `source_to_msg_time DATETIME`
- `source_message_count INT NOT NULL`
- `result_payload JSON NULL`：仅成功 run 保存经过 schema 校验和脱敏的模型输出。
- `failure_code VARCHAR(64)` / `failure_message VARCHAR(500)`
- `started_at DATETIME` / `completed_at DATETIME`
- 唯一约束：`(buyer_nick, completed_fingerprint, prompt_version)`。
- 索引：`(buyer_nick, started_at)`、`(status, started_at)`。

失败信息只存在 run 日志中，不属于可读取的分析结果。

### 9.2 `ai_analysis_v2_events`

- 保存第 6.1 节字段。
- `created_run_id` 指向首次创建该事件的 run，`last_run_id` 指向最后一次延续该事件的成功 run。
- 首次分析一次可产生多个事件，使用 `(created_run_id, event_index)` 唯一约束。
- 索引：`(buyer_nick, event_ended_at)`、`(sentiment_label, event_ended_at)`。

### 9.3 `ai_analysis_v2_issues`

- 保存第 6.2 节字段。
- `event_id` 外键指向 event。
- 冗余 `buyer_nick` 以支持跨客户聚合。
- 索引：`(issue_code, created_at)`、`(status, severity)`、`(buyer_nick, created_at)`。

### 9.4 `ai_analysis_v2_customer_state`

- `buyer_nick` 主键。
- 当前情感、主问题、活跃问题数、最高严重度、attention priority、建议动作。
- `analyzed_through_msg_time` 是唯一增量 checkpoint。
- `last_run_id` 指向最后一次成功 run。

### 9.5 `ai_analysis_v2_reviews`

- `id BIGINT PRIMARY KEY AUTO_INCREMENT`
- `event_id BIGINT UNIQUE NOT NULL`
- `review_status ENUM('pending','approved','corrected','rejected')`
- `model_payload JSON NOT NULL`：审核开始时冻结的模型结果。
- `gold_payload JSON`：人工确认后的最终结果。
- `review_note TEXT` / `reviewed_by VARCHAR(64)` / `reviewed_at DATETIME`。

完整聊天不复制进 V2 表。审核页面按买家和事件时间范围从 `chat_history` 读取，避免重复保存聊天和敏感信息。

## 10. 模型调用和失败策略

1. MiniMax M3 首选，不设置会截断 reasoning 的固定输出 token 上限。
2. JSON/schema 失败时 MiniMax 使用相同输入重试一次。
3. MiniMax 重试仍失败时，仅以下客户允许调用 DeepSeek：
   - `vip_level IN ('V3','V2')`；或
   - `follow_priority IN ('紧急','高')`；或
   - 现有情感或最近 V2 事件为 Negative。
4. 其他客户保持失败可重试，不调用付费模型。
5. 所有提供商失败：run 标为 failed；不写 event、issue、customer state；不推进 checkpoint。
6. 不使用规则引擎生成情感、问题、详情或处理结果。

## 11. API 设计

新增独立路由模块，统一前缀 `/api/v2/ai-analysis-v2`：

- `POST /buyers/{buyer_nick}/analyze`
  - 参数：`mode=full|incremental`。
  - 返回：run、事件、问题和更新后的 customer state。
- `GET /buyers/{buyer_nick}`
  - 返回：customer state、事件历史和问题列表。
- `POST /batch`
  - 创建 V2 批量任务；只分析有新聊天或从未分析的客户。
- `GET /batch/{task_id}` / `POST /batch/{task_id}/cancel`
  - 复用现有批量任务状态格式。
- `GET /trends`
  - 参数：`days=30|90|180`、buyer type、issue category/code、status、severity。
  - 返回：事件数、不同客户数、未解决数、高严重度数、最近出现时间、与前一等长周期的变化。
- `GET /reviews`
  - 返回 50 例审核队列及审核进度。
- `PUT /reviews/{event_id}`
  - 操作：approve、correct、reject。
  - correct/reject 必须有备注；correct 写入 gold payload 并事务更新对应事件、问题和 customer state。

所有新 SQL 放在 `backend/database/sql/ai_analysis_v2/`，不在 Python 中内联业务 SQL。

## 12. 前端闭环

### 12.1 AI 问题洞察页

新增顶层导航“AI 问题洞察”，包含两个子页：

1. **问题趋势**
   - 30/90/180 天切换。
   - 按问题分类、问题编码、状态、严重度和客户类型筛选。
   - 显示问题次数、影响客户数、未解决数、趋势变化和最近出现时间。
   - 点击问题进入受影响客户列表。

2. **人工审核工作台**
   - 左栏：50 例队列和分层标签。
   - 中栏：完整对话和模型证据高亮。
   - 右栏：情感、峰值情绪、多个问题、处理结果、建议动作。
   - 支持批准、修正、拒绝和审核备注。
   - 显示已审核数量、模型分歧数和各字段一致率。

页面沿用现有 Notion 风格，并采用已确认的浅灰背景、白色卡片和深色文字高对比方案。

### 12.2 客户 360° 详情

在 `ChatAnalysis` 增加 V2 当前状态卡片：

- 当前情感与 attention priority。
- 主问题和所有未解决问题。
- 客服处理状态与客户是否接受。
- 建议动作。
- 可展开的历史事件时间线。

### 12.3 Priority List

- 保留现有销售 `follow_priority`。
- 增加 V2 `attention_priority`、主问题和问题状态。
- 最近 V2 Negative 或高严重度未解决问题可进入列表。
- 已处理客户只有出现新的 V2 事件或旧问题状态重新变为 open 才重新进入 pending。

## 13. 50 例审核样本

样本固定为 50 个不同客户，每层 10 个：

1. 当前模型 Negative 或存在明确投诉候选。
2. 真伪、色差、实物不符等高误判风险案例。
3. 产品材质、尺寸、质量和正常退换货案例。
4. 物流、价格、补货和客服沟通摩擦案例。
5. 随机基线案例，覆盖无问题、普通咨询和正面表达。

关键词只用于机械抽样，不用于生成标签。每例必须在工作台中完成人工 approve、correct 或 reject，才计为已审核。

## 14. 测试与发布门禁

### 14.0 当前环境事实

- 项目当前只配置了 `aliyunDB`，数据库为生产 `dunhill`，服务端版本 MySQL 8.0.36。
- 当前生产库只有 `buyer_ai_analysis_cache`、`chat_history` 和 `target_buyers_precomputed` 等 V1 表，5 张 V2 表均不存在。
- 本机存在 MySQL 8.0.24 服务，但项目配置中没有可用的本地数据库账号。
- 在获得可用的本地测试数据库连接前，不允许把 V2 DDL 直接应用到 Aliyun 生产库进行试错。

### 14.1 自动化测试

- schema 校验：缺字段、非法枚举、截断 JSON 必须失败。
- 失败安全：失败 run 不产生 event/issue/state，不推进 checkpoint。
- 多问题：同一事件可保存两个及以上问题。
- 幂等：相同指纹重复运行不产生重复数据。
- 增量：只分析 checkpoint 后的新消息，并能延续旧事件。
- 情感边界：真伪求证、正常退换货、沟通摩擦保持 Neutral；明确投诉保持 Negative。
- 历史衰减：新未解决问题权重高于旧已解决问题。
- 趋势聚合：事件数、不同客户数和对比周期变化与测试数据一致。
- 审核修正：gold payload、事件、问题和 customer state 在同一事务中更新。
- API：所有 V2 路由的成功、失败、分页和筛选契约。
- 前端：TypeScript build 通过；Playwright 覆盖单客户分析、趋势筛选、审核修正和失败重试。

### 14.2 50 例验收阈值

- 50/50 案例完成审核。
- Negative precision = 100%，不允许把求证、正常售后或轻度摩擦误判为 Negative。
- Negative recall ≥ 90%。
- 是否存在问题的一致率 ≥ 90%。
- `issue_code` 一致率 ≥ 80%。
- `resolution_status` 一致率 ≥ 80%。
- 失败结果落库数 = 0。
- 重复事件数 = 0。

阈值未达到时，V2 继续影子运行；允许修 Prompt 和重跑审核样本，但不切换 Priority List 数据源。

### 14.3 发布顺序

1. 在非生产数据库执行 V2 DDL 和集成测试。
2. 实现并验证单客户 full/incremental 分析。
3. 实现 API、客户详情、问题趋势和审核工作台。
4. 生成并审核 50 个真实案例。
5. 达到验收阈值后，经用户确认执行生产数据库迁移。
6. Priority List 改为 V2 优先、V1 fallback。
7. 保留 V1 缓存至少一个完整运营周期，不删除历史数据。

## 15. 明确不包含的范围

- 不重写现有 AI 客户画像模块；它继续使用现有缓存，但沿用失败不缓存的统一约束。
- 不引入向量数据库、消息队列、Redis 状态机或新的前端状态管理库。
- 不让运行时 sub-agent 参与每个客户分析。
- 不删除 V1 表、历史事件、聊天记录或人工修正记录。
- 不在审核通过前自动替换生产 Priority List 的现有数据源。

## 16. 完成定义

只有以下证据全部存在，AI Analysis V2 才能标记完成：

- 5 张 V2 表的 DDL、非生产迁移验证和回滚说明。
- full、incremental、幂等、失败可重试的分析引擎。
- MiniMax 优先且不依赖关键词规则生成语义结果。
- 单客户、多问题、当前状态和跨客户趋势 API。
- 正式问题趋势页、人工审核工作台和客户详情集成。
- 50/50 真实案例审核和验收指标报告。
- 后端测试、前端 build、API 集成测试和 Playwright 全链路通过。
- 用户批准生产迁移和 Priority List 切换。
