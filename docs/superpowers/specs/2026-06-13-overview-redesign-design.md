# Overview 页面改造设计文档

**日期：** 2026-06-13  
**作者：** Claude (Kiro)  
**项目：** SmokeSignal E-Commerce Analytics  
**状态：** 待审批

---

## 1. 概述

### 1.1 改造目标

对 Dashboard Overview 页面进行全面重新设计，从传统的趋势可视化转向群体洞察和可操作的 Action 驱动模式，以更好地服务于小客户池的奢侈品电商业务场景。

### 1.2 核心问题

**现有问题：**
- 传统趋势图表对小客户池（几十到几百个 VIC）统计意义不足
- 缺少群体层面的 AI 分析洞察（目前只有 1v1 客户画像）
- 同期对比组件业务价值不明确
- 缺少库存需求的 Intent 分类
- 定时任务依赖手动触发

**设计原则：**
- 从"展示趋势"转向"提取洞察 + 驱动行动"
- 利用现有 116 个 AI 客户画像，做群体特征聚合
- 双 tab 结构：趋势概览（数据分析）+ 行动看板（可操作任务）
- 所有新功能基于已有的 `target_buyers_precomputed` 和 `buyer_ai_analysis_cache` 表

### 1.3 范围

**包含：**
- Overview 页面结构和组件重设计
- 5 个新 API 端点
- Intent 分类扩展（新增 Inventory Inquiry）
- 定时任务方案设计

**保留现有组件（不做修改）：**
- 4-Group 指标卡片（Customer Health / Follow-up Priority / Sales Opportunities / Service Quality）
- Keyword & Issue Analysis 组件（9 大类关键词分析，针对 SMOKER 客户）
- Priority List 组件（CRM 行动客户列表）

**不包含：**
- Chat & CRM 详情页面修改
- 数据采集和 ETL 流程修改
- 数据库 schema 重大变更（仅新增表和索引）

---

## 2. 架构设计

### 2.1 页面结构

```
Dashboard Overview
├── 全局时间筛选器（顶部）
│   ├── 预设时间段：7D / 15D / 1M / 1Q / 1Y
│   └── 自定义日期范围选择器
├── 4-Group 指标卡片（保留现有）
├── Keyword & Issue Analysis 组件（保留现有，9 大类关键词分析）
└── 双 Tab 内容区
    ├── Tab 1: 趋势概览（数据分析）
    │   ├── VIC 群体画像卡片
    │   ├── 自定义时间对比摘要卡片
    │   └── 客户趋势图表区（2x2 网格）
    │       ├── VIC 客户池规模趋势
    │       ├── VIC 活跃率趋势 ⭐
    │       ├── 高风险客户数量趋势
    │       └── 情感健康度趋势
    └── Tab 2: 行动看板（Action）
        ├── 异常客户预警卡片
        ├── 库存需求组件 ⭐
        └── Priority List 组件（保留现有）
```

### 2.2 技术栈

- **前端：** React 19 + TypeScript + Vite 6 + Recharts 3.6 + Tailwind CSS
- **后端：** FastAPI + MySQL 8.0+
- **AI：** MiniMax M3 → DeepSeek V4 → Rule-based（3 级降级）
- **状态管理：** React Context（时间筛选器状态）
- **数据缓存：** FastAPI 内置缓存 + Redis（可选）

---

## 3. 功能设计

### 3.1 全局时间筛选器

**位置：** Dashboard Overview 页面顶部

**功能：**
- 预设时间段按钮：7D / 15D / 1M / 1Q / 1Y
- 自定义日期范围选择器（DatePicker）
- 全局联动：选择时间范围后，所有依赖时间的组件自动更新

**实现细节：**
- 使用 React Context 或 URL params 存储当前选择的时间范围
- 所有 API 调用带上 `start_date` 和 `end_date` 参数

### 3.2 Tab 1: 趋势概览

#### 3.2.0 Keyword & Issue Analysis 组件（保留）

**位置：** 4-Group 指标卡片下方，双 Tab 内容区上方

**功能：** 9 大类关键词分析（针对 SMOKER 客户）

**9 大类目：**
1. 赠品（Gifts）
2. 包装（Packaging）
3. 维修保养（Maintenance）
4. 退换货（Returns/Exchanges）
5. 产品推荐咨询（Recommendations）
6. 产品参数咨询（Specs）
7. 价格（Price）
8. 物流（Logistics）
9. 投诉反馈（Complaints）

**视觉呈现：**
- Donut 环形图 + 横向柱状图
- 支持客户类型筛选（SMOKER/VIC/BOTH/SEASON/BULK/NON_TARGET）
- 现有 `KeywordAnalysisPanel` 组件，不做修改

**说明：** 此组件保留现有功能，不参与本次改造。

#### 3.2.1 VIC 群体画像卡片

**数据来源：** 聚合所有 VIC 客户的 `buyer_ai_analysis_cache` 表

**展示内容：**
- **关键兴趣特征**：从所有 VIC 的 `key_interests` 字段提取，识别高频且显著的兴趣点
  - 算法：词频 + TF-IDF 加权，筛选出真正有区分度的特征
  - 不限定数量，显示所有超过显著性阈值的兴趣
- **关键痛点特征**：从所有 VIC 的 `pain_points` 字段提取
  - 同样基于显著性判断，不写死数量
- **主流购买动机**：从 `recommended_action` 提取模式

**视觉呈现：**
- 卡片标题：VIC 群体画像 (X 人)
- 3 个子区块（兴趣 / 痛点 / 动机）
- NotionTag 展示关键词，数量由数据特征决定

**API 端点：** `GET /api/v2/insights/vic-persona`

#### 3.2.2 自定义时间对比摘要卡片

**数据来源：** 根据全局时间筛选器选择的时间范围，对比前后两期数据

**时间对比逻辑：**
- 用户选择时间范围：T1 (start_date ~ end_date)
- 自动计算对比期：T0 (前一个等长时间段)
- 例如：选择 2026-05-01 ~ 2026-05-31，对比期自动为 2026-04-01 ~ 2026-04-30

**展示内容：**
- 新增 VIC X 人 / 流失预警 Y 人（T1 vs T0）
- VIP 升级/降级人数（T1 期间内发生的变化）
- 情感转负客户数（T0 期 Positive → T1 期 Negative）
- 标题显示对比时间段

**视觉呈现：**
- 4 个指标横排，数字 + ↑↓ 箭头 + 变化描述
- 配色：正向绿色，负向红色
- 联动全局时间筛选器

**API 端点：** `GET /api/v2/insights/period-comparison?start_date=...&end_date=...`

#### 3.2.3 客户趋势图表区（2x2 网格）

**布局：**
```
┌──────────────────────────┬──────────────────────────┐
│  VIC 客户池规模趋势      │  VIC 活跃率趋势 ⭐       │
│  (堆叠面积图)            │  (折线图)                │
└──────────────────────────┴──────────────────────────┘
┌──────────────────────────┬──────────────────────────┐
│  高风险客户数量趋势      │  情感健康度趋势          │
│  (折线图)                │  (堆叠柱状图)            │
└──────────────────────────┴──────────────────────────┘
```

**数据来源：** `target_buyers_precomputed_history` 按月聚合

**图表 1：VIC 客户池规模趋势**
- 横轴：月份（最近 6 个月）
- 纵轴：VIC 人数
- 分层展示：SMOKER / VIC / BOTH（堆叠面积图）

**图表 2：VIC 活跃率趋势**
- 活跃率定义：当月有购买或有聊天的 VIC 客户占比
- 计算逻辑：
  - 当月活跃 VIC = `(last_purchase_date 在当月) OR (last_chat_date 在当月)`
  - 活跃率 = `当月活跃 VIC 人数 / 当月总 VIC 人数 * 100%`
- 横轴：月份
- 纵轴：活跃率（0-100%）
- 折线图 + 数据点标注百分比

**图表 3：高风险客户数量趋势**
- 横轴：月份
- 纵轴：churn_risk = 'High' 的客户数
- 折线图，可标注运营事件

**图表 4：情感健康度趋势**
- 横轴：月份
- 纵轴：人数
- 堆叠柱状图：Negative / Neutral / Positive

**API 端点：** `GET /api/v2/insights/customer-trends?months=6`

### 3.3 Tab 2: 行动看板

#### 3.3.1 异常客户预警卡片

**数据来源：** 实时计算异常客户

**异常规则：**
1. **情感转负**：上期 Positive → 本期 Negative
2. **购买间隔异常**：当前购买间隔 > 群体平均 × 1.5
3. **聊天频率骤降**：本期聊天数 < 历史月均 × 0.5

**展示内容：**
- 异常客户列表（buyer_nick + 异常原因 + 上次购买日期）
- 点击跳转到 Chat & CRM 详情页

**视觉呈现：**
- 表格形式，最多显示 10 条，可滚动
- 每行：客户昵称 + 红色异常标签 + "查看详情"按钮

**API 端点：** `GET /api/v2/insights/anomaly-alerts`

#### 3.3.2 库存需求组件 ⭐

**功能：** 通过 AI Intent 分类识别有库存需求的客户

**数据识别流程：**

**Step 1: 扩展 Intent 分类**
- 现有 5 类 intent：Pre-sale Inquiry / Post-sale Support / Logistics / Usage Guide / Complaint
- 新增第 6 类：Inventory Inquiry（库存查询）
- 定义：客户询问产品库存、补货时间、到货情况、缺货问题

**Step 2: 更新 AI Prompt**
- 修改 `backend/ai/prompts/sentiment_intent_prompt.py`
- 加入 Inventory Inquiry 定义和示例对话

**Step 3: 测试验证**
- 从 `chat_history` 表筛选 10-20 个包含库存关键词的真实客户
- 手动触发这些客户的 AI 分析
- 验证识别准确率（目标 >= 80%）

**Step 4: 数据积累**
- 不回填历史数据
- 从测试通过后开始，所有新对话自动识别新 intent

**展示内容：**
- 库存需求列表（不限制条数，用滑动条展示所有）
- 每条需求包含：
  - 客户昵称（可点击跳转详情）
  - VIP 等级标签
  - Intent 分布（如 "库存查询 60% | 售前咨询 40%"）
  - 最近聊天时间
  - 情感标签
  - 操作按钮：查看详情 / 标记已联系

**排序规则：**
- VIP 等级 DESC → 最近聊天时间 DESC

**API 端点：** `GET /api/v2/action/inventory-inquiries`

#### 3.3.3 Priority List 组件

**保留现有组件，不做修改。**

---

## 4. 定时任务设计

### 4.1 需求

定时自动刷新所有客户的 Persona + Sentiment/Intent 分析，在凌晨执行（大模型额度重置，低峰期）。

### 4.2 方案选择

**短期方案（开发阶段）：** 数据库 Event + 开机补跑
- MySQL Event 每日凌晨标记需要刷新的客户（写入 `ai_refresh_queue` 表）
- 电脑下次开机启动 FastAPI 时，自动检查队列并补跑积压任务
- 成本：¥0

**长期方案（生产环境）：** APScheduler（集成在 FastAPI）
- 部署到云服务器后，使用 APScheduler 每日凌晨 2:00 自动执行
- 集成在 FastAPI 进程内，无需额外配置

### 4.3 短期方案实现（开机补跑）

#### 数据库层

**1. 创建刷新队列表：**

```sql
CREATE TABLE ai_refresh_queue (
    id INT PRIMARY KEY AUTO_INCREMENT,
    buyer_nick VARCHAR(255) NOT NULL,
    priority INT NOT NULL COMMENT '1=V3/V2, 2=V1/V0, 3=其他',
    reason VARCHAR(50) COMMENT 'new_purchase/new_chat/30days_outdated',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    processed_at TIMESTAMP NULL,
    UNIQUE KEY uk_buyer_pending (buyer_nick, status),
    INDEX idx_status_priority (status, priority, created_at)
);
```

**2. 创建 MySQL Event（每日凌晨 2:00 标记）：**

```sql
CREATE EVENT daily_mark_refresh_queue
ON SCHEDULE EVERY 1 DAY STARTS '2026-06-14 02:00:00'
DO
  INSERT INTO ai_refresh_queue (buyer_nick, priority, reason)
  SELECT 
    tb.buyer_nick,
    CASE 
      WHEN tb.vip_level IN ('V3', 'V2') THEN 1
      WHEN tb.vip_level IN ('V1', 'V0') THEN 2
      ELSE 3
    END as priority,
    CASE
      WHEN tb.last_purchase_date > COALESCE(ai.analyzed_last_purchase_date, '1970-01-01') THEN 'new_purchase'
      WHEN tb.last_chat_date > COALESCE(ai.analyzed_last_chat_date, '1970-01-01') THEN 'new_chat'
      WHEN DATEDIFF(CURDATE(), ai.persona_analyzed_at) > 30 THEN '30days_outdated'
    END as reason
  FROM target_buyers_precomputed tb
  LEFT JOIN buyer_ai_analysis_cache ai ON tb.buyer_nick = ai.buyer_nick
  WHERE tb.last_purchase_date > COALESCE(ai.analyzed_last_purchase_date, '1970-01-01')
     OR tb.last_chat_date > COALESCE(ai.analyzed_last_chat_date, '1970-01-01')
     OR DATEDIFF(CURDATE(), ai.persona_analyzed_at) > 30
  ON DUPLICATE KEY UPDATE created_at = CURRENT_TIMESTAMP;
```

#### 后端层

**1. 创建队列处理模块 `backend/tasks/queue_processor.py`：**

```python
class AIRefreshQueueProcessor:
    async def process_pending_queue(self, max_count: int = 200):
        """处理队列中的待刷新客户"""
        # 查询 pending 状态的客户，按 priority ASC 排序
        # 每批 10 个并发刷新
        # 批次间间隔 5 秒
        # 更新状态为 completed/failed
        pass
```

**2. FastAPI 启动时自动检查队列：**

```python
@app.on_event("startup")
async def startup_event():
    processor = AIRefreshQueueProcessor()
    # 非阻塞方式启动队列处理
    asyncio.create_task(processor.process_pending_queue())
```

### 4.4 长期方案实现（APScheduler）

部署到云服务器后，切换到 APScheduler：

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.tasks.ai_refresh import daily_refresh_task

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=2, minute=0)
async def daily_refresh_ai_analysis():
    """每日凌晨 2:00 批量刷新 AI 分析"""
    await daily_refresh_task(max_count=200)

@app.on_event("startup")
async def startup_event():
    scheduler.start()
```

### 4.5 监控与日志

**创建刷新日志表：**

```sql
CREATE TABLE ai_refresh_log (
    id INT PRIMARY KEY AUTO_INCREMENT,
    refresh_date DATE NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    total_customers INT NOT NULL,
    successful_count INT NOT NULL,
    failed_count INT NOT NULL,
    minimax_calls INT DEFAULT 0,
    deepseek_pro_calls INT DEFAULT 0,
    deepseek_flash_calls INT DEFAULT 0,
    estimated_cost DECIMAL(10, 2) COMMENT '预估成本（元）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**管理 API：**
- `GET /api/v2/admin/refresh-status` - 查看上次刷新结果
- `POST /api/v2/admin/trigger-refresh` - 手动触发刷新（测试用）

---

## 5. API 设计

### 5.1 新增 API 端点列表

| 端点 | 方法 | 功能 | 参数 |
|------|------|------|------|
| `/api/v2/insights/vic-persona` | GET | VIC 群体画像 | - |
| `/api/v2/insights/period-comparison` | GET | 时间对比摘要 | start_date, end_date |
| `/api/v2/insights/anomaly-alerts` | GET | 异常客户预警 | - |
| `/api/v2/action/inventory-inquiries` | GET | 库存需求列表 | - |
| `/api/v2/insights/customer-trends` | GET | 客户趋势数据 | months (默认 6) |
| `/api/v2/admin/refresh-status` | GET | 刷新任务状态 | - |
| `/api/v2/admin/trigger-refresh` | POST | 手动触发刷新 | max_count |

### 5.2 API 响应示例

**VIC 群体画像：**

```json
{
  "total_vic_count": 116,
  "key_interests": [
    {"keyword": "高端烟斗收藏", "count": 45, "percentage": 38.8},
    {"keyword": "限量版产品", "count": 38, "percentage": 32.8}
  ],
  "key_pain_points": [
    {"keyword": "尺码选择困难", "count": 28, "percentage": 24.1}
  ],
  "purchase_motivations": [
    {"pattern": "复购老客户", "count": 58}
  ]
}
```

**时间对比摘要：**

```json
{
  "current_period": {
    "start_date": "2026-05-01",
    "end_date": "2026-05-31"
  },
  "comparison_period": {
    "start_date": "2026-04-01",
    "end_date": "2026-04-30"
  },
  "metrics": {
    "new_vic": {"current": 8, "previous": 5, "change": 3, "change_pct": 60.0},
    "churn_warning": {"current": 12, "previous": 15, "change": -3, "change_pct": -20.0}
  }
}
```

**客户趋势数据：**

```json
{
  "vic_pool_trend": [
    {"month": "2026-01", "SMOKER": 45, "VIC": 82, "BOTH": 38}
  ],
  "vic_active_rate_trend": [
    {"month": "2026-01", "total_vic": 120, "active_vic": 78, "active_rate": 65.0}
  ],
  "high_risk_trend": [
    {"month": "2026-01", "high_risk_count": 22}
  ],
  "sentiment_trend": [
    {"month": "2026-01", "Positive": 68, "Neutral": 42, "Negative": 10}
  ]
}
```

**异常客户预警：**

```json
{
  "anomalies": [
    {
      "buyer_nick": "buyer_001",
      "vip_level": "V3",
      "anomaly_type": "sentiment_negative",
      "anomaly_reason": "上月 Positive → 本月 Negative",
      "last_purchase_date": "2026-04-15",
      "last_chat_date": "2026-05-20",
      "severity": "high"
    }
  ],
  "total_count": 15
}
```

**库存需求列表：**

```json
{
  "inquiries": [
    {
      "buyer_nick": "buyer_003",
      "vip_level": "V3",
      "dominant_intent": "Inventory Inquiry",
      "intent_distribution": {
        "Inventory Inquiry": 0.65,
        "Pre-sale Inquiry": 0.35
      },
      "sentiment_label": "Neutral",
      "last_chat_date": "2026-06-10",
      "total_chat_messages": 28
    }
  ],
  "total_count": 8
}
```

---

## 6. 性能优化

### 6.1 缓存策略

| API | 缓存时长 | 理由 |
|-----|----------|------|
| VIC 群体画像 | 24 小时 | 群体特征变化慢 |
| 客户趋势数据 | 1 小时 | 历史数据变化慢 |
| 异常客户预警 | 无缓存 | 需要实时识别 |
| 库存需求列表 | 30 分钟 | 准实时即可 |

### 6.2 数据库优化

**新增索引：**

```sql
-- buyer_ai_analysis_cache 表
CREATE INDEX idx_dominant_intent ON buyer_ai_analysis_cache(dominant_intent);
CREATE INDEX idx_sentiment_label ON buyer_ai_analysis_cache(sentiment_label);

-- ai_refresh_queue 表
CREATE INDEX idx_status_priority ON ai_refresh_queue(status, priority, created_at);
```

### 6.3 并发查询

Dashboard Overview 的多个 API 并行调用：

```typescript
const [vicPersona, trends, anomalies] = await Promise.all([
  fetch('/api/v2/insights/vic-persona'),
  fetch('/api/v2/insights/customer-trends?months=6'),
  fetch('/api/v2/insights/anomaly-alerts')
]);
```

---

## 7. 错误处理

### 7.1 API 层错误处理

1. **数据库连接失败** → 503 Service Unavailable
2. **AI 分析失败** → 多级降级（MiniMax → DeepSeek → Rule-based）
3. **History 表数据缺失** → 前端跳过缺失月份，显示提示
4. **空数据处理** → 显示友好提示："数据积累中，请稍后查看"

### 7.2 前端错误显示

- 使用 ErrorAlert 组件统一显示错误
- 提供重试按钮
- 关键错误记录到日志

---

## 8. 部署方案

### 8.1 开发阶段（现在）

- 本地开发：前端 `npm run dev`，后端 `python -m backend.main`
- 定时任务：数据库 Event + 开机补跑方案
- 成本：¥0

### 8.2 生产环境（项目稳定后）

**推荐方案：全栈云服务器部署**
- 平台：阿里云轻量应用服务器（2 核 2G）
- 成本：约 ¥30-60/月
- 部署方式：
  - Nginx 反向代理
  - `/` 路由到 React 前端
  - `/api` 路由到 FastAPI 后端
  - 定时任务切换到 APScheduler

**或：前后端分离部署**
- 前端 → Vercel（免费）
- 后端 → 阿里云服务器（¥30-60/月）

---

## 9. 实施计划

### Phase 1: 基础设施（1-2 天）

**1. 数据库准备**
- 创建 `ai_refresh_queue` 表
- 创建 `ai_refresh_log` 表
- 创建 MySQL Event（标记待刷新客户）
- 新增索引

**2. 后端基础**
- 实现 `AIRefreshQueueProcessor` 类
- FastAPI 启动时自动处理队列

### Phase 2: Intent 分类扩展（2-3 天）

1. 更新 AI Prompt（加入 Inventory Inquiry）
2. 测试验证（10-20 个真实客户样本）
3. 如果准确率 >= 80%，进入下一阶段；否则调整 Prompt

### Phase 3: API 开发（3-4 天）

1. 实现 5 个新 API 端点
2. 添加单元测试
3. 测试缓存策略

### Phase 4: 前端开发（5-7 天）

1. 全局时间筛选器组件
2. 趋势概览 tab：
   - VIC 群体画像卡片
   - 自定义时间对比摘要卡片
   - 4 个趋势图表
3. 行动看板 tab：
   - 异常客户预警卡片
   - 库存需求组件
4. 保留组件集成：
   - 4-Group 指标卡片（已有）
   - Keyword & Issue Analysis 组件（已有，9 大类关键词分析）
   - Priority List 组件（已有）
5. 集成测试

### Phase 5: 测试与优化（2-3 天）

1. 端到端测试
2. 性能优化
3. 错误处理测试
4. 用户验收测试

### Phase 6: 部署（1-2 天）

1. 提交代码到 Git
2. 更新文档
3. 部署到生产环境（如果需要）

**总预估时间：** 14-21 天

---

## 10. 风险与挑战

### 10.1 技术风险

1. **AI Intent 识别准确率不足**
   - 缓解措施：充分测试，准备回退到关键词匹配方案
   
2. **History 表数据缺失**
   - SEASON/BULK 客户类型没有历史数据
   - 缓解措施：趋势图表仅展示有历史数据的客户类型

3. **定时任务执行失败**
   - 缓解措施：完善日志记录，设置告警通知

### 10.2 业务风险

1. **群体洞察提取效果不佳**
   - AI 画像数据质量参差不齐
   - 缓解措施：设置最小样本量阈值，小于阈值时显示提示

2. **用户不习惯新界面**
   - 缓解措施：保留关键原有功能，提供使用引导

---

## 11. 成功指标

### 11.1 技术指标

- [ ] API 响应时间 < 500ms（除趋势图表 API）
- [ ] 趋势图表 API 响应时间 < 2s
- [ ] 前端首屏加载时间 < 3s
- [ ] AI Intent 识别准确率 >= 80%

### 11.2 业务指标

- [ ] 客服使用库存需求功能，响应效率提升
- [ ] 异常客户预警命中率（需跟踪实际流失情况）
- [ ] 用户对新界面的满意度反馈

---

## 12. 后续优化方向

1. **群体洞察深化**
   - 客户分群对比（V3 vs V1 特征差异）
   - 时间维度的群体特征变化

2. **Action 功能扩展**
   - 客服操作记录与效果追踪
   - 批量触达功能

3. **智能推荐**
   - 基于群体特征推荐营销策略
   - 基于异常模式推荐干预措施

---

**设计文档完成日期：** 2026-06-13  
**下一步：** 进入实施阶段，创建详细的技术实现计划
