# target_buyers_precomputed 历史快照架构改造

> 实施计划 + 状态追踪。每个任务完成后更新本文件。
> 最后更新：2026-06-03（demo 阶段完成）

---

## 0. 当前状态（动态更新）

| 阶段 | 状态 | 完成日期 | 备注 |
|---|---|---|---|
| **Demo 探索** | ✅ 完成 | 2026-06-03 | 见 §6 |
| **P1: DDL 建表（带 partition）** | ⏳ 待开始 | | |
| **P2: 每日 snapshot procedure** | ⏳ | | |
| **P3: 月度 partition 维护 procedure** | ⏳ | | |
| **P4: 告警机制** | ⏳ | | |
| **P5: 回填脚本（生产规模）** | ⏳ | | 14M 累积 |
| **P6: 查询 SQL 文件** | ⏳ | | |
| **P7: analyzer 集成** | ⏳ | | |
| **P8: API endpoints** | ⏳ | | |
| **P9: 前端 UI** | ⏳ | | |

---

## 1. Context

### 1.1 业务问题

`target_buyers_precomputed` 当前只保留**最新一日的快照**（PK = `buyer_nick`，每天 11:00 MySQL event 全量重算后覆盖）。这导致以下业务场景**无法回答**：

- **VIC YoY 对比**：今年 6 月的 VIC 池子跟去年同期相比，规模/贡献/结构变化如何？
- **SEASON 客户对比**：同期 SEASON 客户数、贡献、转化趋势？
- **Negative 客户趋势**：随时间推移，Negative 客户数是否在被前端客服介入后变少？

### 1.2 关键约束

| 约束 | 原因 |
|---|---|
| **v2 API 0 改动** | 现有 14 个测试在跑 |
| **SEASON 不回填** | SEASON 是新增 buyer_type，无历史定义 |
| **VIC 走真实 rolling24M** | 回填时用"那一天往前 rolling24M"重新判定 |
| **回填起点 2025-04-01** | 距今 14M，足够支撑 YoY |
| **daily pool 1k-10k** | 24M 保留 = 上限 730 万行 |

### 1.3 chat / AI 字段不进 history

- `chat_frequency_days` / `total_chat_messages` / `last_chat_date` / `l30d_chat_frequency_days` / `l3m_chat_frequency_days` / `avg_chat_interval_days`：chat_history 从 2025-H2 才有完整数据，回填行不计算
- `sentiment_label` / `sentiment_score` / `dominant_intent` / `pre_sale_score` / `post_sale_score` / `complaint_tendency`：需要 LLM 调用，**不进 history**
- AI 字段**留 live 主表**，按现有节奏由 AI job 更新
- 如果确实要 sentiment 历史趋势，新建 `target_buyers_sentiment_history`（方案 D），**仅在 AI 真正跑过该买家时写入一行**

---

## 2. 设计决策（已确认 2026-06-03）

| 决策项 | 选择 |
|---|---|
| 存储策略 | 独立 history 表，原表不动 |
| 粒度 | 每日 snapshot |
| 保留时长 | 24 个月 |
| 回填范围 | 2025-04-01 起每日回填；SEASON 客户不回填 |
| CS 介入数据 | 复用 chat_history，不加新表 |
| 容错机制 | 幂等 + 告警（失败发 email；不重试） |
| 分区粒度 | 按月 RANGE PARTITION |
| sentiment 回填 | 不回填，sentiment = 'Unknown' |
| churn_risk | R+F 组合（用户决策） |
| RFM segment | 复用主表 13 类中文 CASE（去掉 F=2 的 chat 依赖） |

---

## 3. 存储设计

### 3.1 新表 `target_buyers_precomputed_history`

40 字段（v2 demo 已确认），全部 ASOF 可算：

| 类别 | 字段 |
|---|---|
| 标识 | buyer_nick, channel, client_monthly_tag |
| 类型 | is_smoker, is_vic, buyer_type, vip_level |
| 累计 | historical_gmv, historical_refund, historical_net_sales, total_orders, total_net_orders, refund_rate |
| Rolling 24M | rolling_24m_gmv, rolling_24m_netsales, rolling_24m_orders, rolling_24m_net_orders |
| L6M | l6m_gmv, l6m_netsales, l6m_orders, l6m_refund_rate |
| L1Y | l1y_gmv, l1y_netsales, l1y_orders, l1y_refund_rate |
| 频率 | avg_purchase_interval_days |
| 折扣 | discount_ratio, discount_sensitivity |
| 时间边界 | first_purchase_date, last_purchase_date, city |
| 品类 | top_category, second_category, third_category |
| RFM | rfm_recency_score, rfm_frequency_score, rfm_monetary_score, rfm_segment, churn_risk |
| 时间维度 | snapshot_date |

### 3.2 Partition

```sql
PARTITION BY RANGE (TO_DAYS(snapshot_date)) (
    PARTITION p202504 VALUES LESS THAN (TO_DAYS('2025-05-01')),
    -- ... 每月一个 ...
    PARTITION p_future VALUES LESS THAN MAXVALUE
);
```

---

## 4. 关键算法（复用主表 procedure 逻辑）

### 4.1 Smoker 识别（asof d）

```sql
-- 主表 procedure: 无时间过滤（因为 NOW() 隐式）
-- history backfill: 加 < d 过滤（否则会包含未来才买的客户）
SELECT DISTINCT 买家昵称, 1, 0, 'SMOKER'
FROM dunhill_t01_trade_line
WHERE category IN ('Pipes', 'Lighters')
  AND 买家昵称 IS NOT NULL AND 买家昵称 != ''
  AND 最后付款时间 < d  -- 关键
```

### 4.2 VIC 识别（asof d）

```sql
SELECT 买家昵称, 0, 1, 'VIC'
FROM dunhill_t01_trade_line
WHERE 最后付款时间 < d
  AND 最后付款时间 >= DATE_SUB(d, INTERVAL 24 MONTH)
  AND 买家昵称 IS NOT NULL AND 买家昵称 != ''
GROUP BY 买家昵称
HAVING SUM(成交总金额 - IFNULL(退款金额, 0)) >= 30000
```

### 4.3 RFM segment（13 类主表同款）

直接复用主表 `refresh_target_buyers_precomputed_procedure.sql` 的 Phase 5a/5b 逻辑，参数化 `NOW()` → `d`。

### 4.4 churn_risk（R + F 组合）

```sql
CASE
    WHEN last_purchase_date IS NULL THEN '低'
    WHEN rfm_r = 1 THEN '高'
    WHEN rfm_r = 2 THEN '高'
    WHEN rfm_r = 3 AND rfm_f >= 4 THEN '中'
    WHEN rfm_r = 3 THEN '中'
    WHEN rfm_r = 4 AND rfm_f <= 2 THEN '中'
    ELSE '低'
END
```

---

## 5. 分支策略

| 分支 | 内容 | base | 状态 |
|---|---|---|---|
| `chore/cleanup-runtime-artifacts-and-legacy` | .gitignore + .gitattributes + 删除 runtime artifacts | main | ✅ PR 待用户开 |
| `feature/target-buyers-history-schema` | P1-P4 DDL + procedure + event | main | ⏳ |
| `feature/target-buyers-history-backfill` | P5 一次性回填脚本 | main | ⏳ |
| `feature/target-buyers-history-api` | P6-P8 SQL + analyzer + API | main | ⏳ |
| `feature/target-buyers-history-ui` | P9 前端 | main | ⏳ |

按 schema → backfill → api → ui 顺序合并到 main。

---

## 6. Demo 阶段已完成（2026-06-03）

### 6.1 Demo 数据

- **表**: `target_buyers_precomputed_history_demo` (Aliyun 生产库, _demo 后缀避免污染)
- **回填范围**: 2025-04-01 → 2025-04-30 (30 天)
- **总行数**: 6,689 (224 买家 × 30 天)
- **表大小**: 2.59 MB
- **24M 估算**: ~16 万行 / 62 MB
- **主表未受影响**: target_buyers_precomputed 仍 548 行

### 6.2 池子动态变化（30 天实证）

| 时间 | 池子 | 变化 |
|---|---|---|
| 04-01 ~ 04-14 | 222 | 稳定 |
| 04-15 | 223 | +1 VIC 进入 rolling 24M |
| 04-16 | 224 | +1 VIC 进入 rolling 24M |
| 04-29 | 223 | -1 VIC 滑出 rolling 24M |
| 04-30 | 223 | |

**新增 2 人**: DUNWEB0000027342, tb2503300_2012 (VIC)
**流失 1 人**: 醉闻兰花香 (VIC)

### 6.3 Demo 验证的关键点（已 OK）

- [x] 池子 222 是 procedure 在 2025-04-01 跑的真实结果
- [x] 抽样客户 (eddendeng, laoliu0218, tb7235476306) 数据合理
- [x] 22 个 0 sales 客户经查都是**全额退款的 Smoker 客户**（真实情况）
- [x] RFM segment 跟主表 13 类一致
- [x] Smoker 池 30 天内不变（4 月无新 Pipes/Lighters 交易）

### 6.4 Demo 脚本（6 个，未跟踪）

位置：`scripts/demo_*.py` 和 `scripts/demo_v2_*.py`

| 文件 | 内容 |
|---|---|
| `demo_create_history_table.py` | v1 建表（22 字段，旧） |
| `demo_backfill_week.py` | v1 backfill（7 天，已废弃） |
| `demo_inspect_data.py` | v1 检视 |
| `demo_v2_create_tables.py` | v2 建表（40 字段 + sentiment_history DDL） |
| `demo_v2_backfill.py` | v2 backfill（**当前用这个**） |
| `demo_v2_inspect.py` | v2 检视 |

**处理方式**: P1 实施时迁入 `feature/target-buyers-history-schema` 分支，作为历史起点 + 单元测试用。

---

## 7. 用户工作流规则（2026-06-03 确认）

### 7.1 Commit / Branch 规则

1. **大工程/大变动前必须先 commit**
2. **必要时开新分支**（不要在 main / 旧分支直接动）
3. **每个任务完成更新 plan**（本文件）
4. **Plan mode 写大方案的详细实施计划**

### 7.2 Fetch 失败处理（memory 已存）

- `git fetch origin` 失败时**立即停止**，告诉用户
- 不要靠 `git branch -f` 拼凑 / 靠缓存继续
- SSH 在本项目网络下比 HTTPS 稳定

---

## 8. 实施 checklist

### PR1: Schema + Procedure (P1-P4)

- [ ] 建新分支 `feature/target-buyers-history-schema` (基于 main)
- [ ] commit 6 个 demo 脚本到该分支（作为历史起点）
- [ ] P1: `create_target_buyers_precomputed_history.sql`（DDL + 24M partition）
- [ ] P2: `snapshot_target_buyers_history()` procedure + 11:30 event
- [ ] P3: `maintain_history_partitions()` procedure + 每月 event
- [ ] P4: `send_alert_email()` 简化版告警
- [ ] 在 staging 跑 demo_v2 验证
- [ ] PR 提交 + 等用户 review
- [ ] 合并到 main

### PR2: Backfill (P5)

- [ ] 等 PR1 merge
- [ ] 建新分支 `feature/target-buyers-history-backfill` (基于 main)
- [ ] 抽离 `refresh_target_buyers_asof(as_of_date)` 参数化 procedure
- [ ] Python 脚本 backfill 2025-04-01 → 2026-06-02
- [ ] 进度持久化 + 避峰（凌晨跑）
- [ ] 监控一周

### PR3: API (P6-P8)

- [ ] 等 PR2 merge
- [ ] 建新分支 `feature/target-buyers-history-api`
- [ ] 5 个查询 SQL 文件到 `backend/database/sql/target_buyers/history_*.sql`
- [ ] `TargetBuyerQueries` 类加 5 个方法
- [ ] `TargetBuyerAnalyzer` 类加 5 个方法
- [ ] `target_routes.py` 加 5 个 v2 endpoint
- [ ] 测试

### PR4: UI (P9)

- [ ] 等 PR3 merge
- [ ] 建新分支 `feature/target-buyers-history-ui`
- [ ] Configuration 视图加对比面板
- [ ] YoY/MoM 切换
- [ ] Negative 趋势图
- [ ] 单买家 sentiment 折线（如果方案 D 落地）

---

## 9. 不在本次范围

- 数据仓库方向（Star Schema / Fact-Dim）
- 任意时间点 AS-OF 查询
- Real-time CDC
- 历史 sentiment 真实回填
- 动态 SQL 模板生成器
- BI 工具集成
- 重构现有 v2 API 逻辑

---

## 10. 进度日志

| 日期 | 状态 | 备注 |
|---|---|---|
| 2026-06-03 | Demo 阶段完成 | 30 天数据写入 demo 表，池子动态变化可见 |
| | | |
