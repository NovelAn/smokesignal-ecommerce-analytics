# CRM 运营增强 Round 1 — 设计文档

> 基于历史快照数据增强客服触达、运营监控和分析对比。Round 1 聚焦：流失预警 + 健康度对比 + YoY 分析。
> 不碰预计算表结构，新增独立 `customer_service_log` 表。

## 范围

| 模块 | 说明 | 依赖 |
|---|---|---|
| PriorityAttentionBoard 增强 | +流失预警 tab + 处理标记 + segment 退化列 | customer_service_log 表, history API |
| MetricCards 对比值 | 每 card 底部 △ vs 30D 前 | 扩展 dashboard_metrics SQL |
| YoY 对比图 | 替换现有 HistoryTrendsSection, 自定义日期 | 复用现有 5 history API |
| customer_service_log 表 | 客服操作记录 (不碰预计算表) | 新 DDL |

Round 2 后续：库存/补货需求分类 (第 10 关键词分类)。

---
## customer_service_log 表

```sql
CREATE TABLE customer_service_log (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    buyer_nick  VARCHAR(255) NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'pending'
                COMMENT 'pending / contacted / resolved',
    notes       TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_buyer (buyer_nick),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

API:
- `POST /api/v2/service/mark` { buyer_nick, status, notes } → UPSERT
- `GET /api/v2/service/history/{buyer_nick}` → 该客户所有处理记录

---
## Rolling Window 重触发机制

已处理客户 (status = contacted/resolved) 的再出现条件 = **2 层信号**:

### Layer 1: 即时事件 (立即重触发)
- processed_at 之后出现新 Negative 聊天 (sentiment_label = 'Negative')
- processed_at 之后出现新退款订单 (退款金额 > 0)

### Layer 2: 累计退化 (长期信号)
- segment 退化: 重要价值/保持 → 潜力/待激活/已流失
- churn_risk 上升: 低/中 → 高

数据源: history 表最接近 processed_at 的 snapshot_date → 对比现在 precomputed 表。

---
## PriorityAttentionBoard 改动

```
PriorityAttentionBoard
├─ TabBar: ["需优先跟进", "流失预警"]
│
├─ Tab 1: 需优先跟进 (现有逻辑 + 增强)
│   ├─ LEFT JOIN customer_service_log
│   ├─ 已处理客户重触发用 Rolling Window
│   ├─ 每行: [标记已处理] 按钮 → POST /service/mark
│   ├─ 新增列: "上次处理时间" (csl.updated_at)
│   └─ 新增列: "退化信号" (如有 segment/churn 退化)
│
└─ Tab 2: 流失预警 (新)
    ├─ 数据源: history 表 30D segment 对比
    ├─ 逻辑: rfm_segment 退化 + churn_risk 上升
    └─ 列: nick | segment变化 | churn变化 | l6m降幅 | 操作
```

API:
- `GET /api/v2/priority-customers` — 加 JOIN + Rolling Window 条件
- `GET /api/v2/history/churn-warning` — 新 endpoint: segment 退化列表

---
## MetricCards 改动

现有 4 组 card 底部各加一行对比值:

```
客户健康度
  Positive: 320  Negative: 45
  △ Negative +8 (vs 30D前)

跟进优先级
  紧急: 12  高: 38
  △ 紧急 -3 (vs 30D前)
```

后端: `get_dashboard_metrics` SQL 加 30D 前子查询，返回 `_30d_ago` 字段。

---
## YoY 对比图 (替换 HistoryTrendsSection)

现有 HistoryTrendsSection 删除。新组件 `YoYCompareChart`:

- 顶部: 日期选择器 (from → to) + 对比模式 (YoY/MoM/自定义)
- 图表: 双色双线 (今年蓝 + 去年灰) + △ 标签
- 底部: 3 个总结卡 (池子/VIC/Negative 变化%)
- 数据源: 复用现有 5 history API (无需新后端)

---
## 改动文件汇总

| 文件 | 改动类型 | 行数(估) |
|---|---|---|
| `customer_service_log.sql` | 新 DDL | +12 |
| `get_churn_warning.sql` | 新 SQL | +30 |
| `get_priority_customers.sql` | SQL 改 (JOIN + EXISTS) | +20 |
| `get_dashboard_metrics.sql` | SQL 改 (30D 对比) | +15 |
| `target_routes.py` | +3 endpoint | +60 |
| `target_buyer_queries.py` | +3 method | +40 |
| `target_buyer_analyzer.py` | +3 method | +30 |
| `client.ts` | +3 type + 3 method | +40 |
| `PriorityAttentionBoard.tsx` | +Tab + 标记按钮 + 退化列 | +120 |
| `MetricCards.tsx` | +△ 对比值行 | +30 |
| `YoYCompareChart.tsx` | 新组件 | +200 |
| `DashboardOverview.tsx` | 替换 HistoryTrendsSection | +3/-3 |

共 12 文件, ~600 行新代码。

---
## 已验证的设计决策

- [x] 预计算表不动，新表 customer_service_log
- [x] follow_priority 两阶段计算 (Phase 5c + 6b)
- [x] Rolling Window = 即时事件 + 累计退化两层
- [x] Tab 2 流失预警用 history 表 segment 对比
- [x] MetricCards △ 值显示 30D 前对比
- [x] YoY 对比图替换 HistoryTrendsSection
- [x] Round 2: 库存/补货需求分类 (第 10 类)
