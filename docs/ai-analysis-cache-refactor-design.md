# AI分析缓存表架构重构设计文档

> **文档版本**: v2.0
> **创建日期**: 2026-02-26
> **最后更新**: 2026-02-26
> **状态**: 待评审

---

## 目录

1. [背景与问题](#1-背景与问题)
2. [设计目标](#2-设计目标)
3. [架构方案](#3-架构方案)
4. [存储过程更新](#4-存储过程更新)
5. [代码修改清单](#5-代码修改清单)
6. [迁移计划](#6-迁移计划)
7. [测试验证](#7-测试验证)

---

## 1. 背景与问题

### 1.1 当前架构

系统中有两种AI分析任务：

| 分析类型 | 功能 | 入口文件 | 存储字段 |
|---------|------|---------|---------|
| **AI客户画像分析** | 生成客户画像、兴趣点、痛点、推荐行动 | `analyzer_orchestrator.py` | `summary`, `key_interests`, `pain_points`, `recommended_action` |
| **情感/意图分析** | 分析客户情绪和聊天意图 | `batch_analyzer.py` | `sentiment_score`, `sentiment_label`, `intent_distribution`, `dominant_intent` |

两者都使用 `buyer_ai_analysis_cache` 表存储结果。

### 1.2 存在的问题

#### 问题1: 无法独立判断是否需要更新

```
当前问题:
├── 两类分析共用同一条记录，字段混杂
├── 无法独立判断某种分析是否需要更新
└── 画像和情感的更新条件不同，但无法分别判断
```

#### 问题2: 增量更新判断不明确

- **AI客户画像**: 何时需要重新分析？(新订单? 新聊天?)
- **情感/意图分析**: 何时需要重新分析？(新聊天? 聊天数量阈值?)
- **如何知道分析后是否有新数据产生？**

当前缺乏明确的判断标准和数据快照机制。

#### 问题3: 存储过程与AI分析脱节

`refresh_target_buyers_precomputed` 存储过程：
- ✅ 已包含RFM计算逻辑
- ❌ 情感/意图字段无数据来源
- ❌ 未从缓存表读取AI分析结果

---

## 2. 设计目标

### 2.1 核心目标

1. **独立更新判断**: 画像和情感分析可独立判断是否需要更新
2. **纯增量更新**: 基于数据快照判断，只有数据变化才重新分析
3. **存储过程集成**: 自动从缓存表读取AI分析结果到预计算表
4. **触发条件明确**: 定义清晰的分析触发条件

### 2.2 关键设计决策

| 决策项 | 选择 | 说明 |
|--------|------|------|
| **缓存表结构** | 一个客户一条记录 | 画像和情感字段分开存储在同一记录中 |
| **增量判断** | 数据快照时间戳 | 存储 `analyzed_last_purchase_date`, `analyzed_last_chat_date` |
| **TTL机制** | ❌ 删除 | 纯增量更新，无过期时间 |
| **情感分析门槛** | 聊天天数 ≥ 10 | 低于此阈值不触发分析 |
| **强制刷新** | 手动API | 异常情况下可手动触发重新分析 |

### 2.3 约束条件

- 保持向后兼容，现有API无需修改
- 不创建新表，在现有表结构上扩展
- 分析任务可独立触发，也可同时触发

---

## 3. 架构方案

### 3.1 缓存表结构重构

#### 3.1.1 完整表结构（一个客户一条记录）

```sql
CREATE TABLE buyer_ai_analysis_cache (
    -- 主键
    buyer_nick              VARCHAR(100) PRIMARY KEY COMMENT '买家昵称',

    -- 画像分析独立时间戳
    persona_analyzed_at             TIMESTAMP NULL COMMENT '画像分析完成时间',
    persona_analyzed_last_purchase_date TIMESTAMP NULL COMMENT '画像分析时的最后订单时间',
    persona_analyzed_last_chat_date TIMESTAMP NULL COMMENT '画像分析时的最后聊天时间',

    -- 情感分析独立时间戳
    sentiment_analyzed_at           TIMESTAMP NULL COMMENT '情感分析完成时间',
    sentiment_analyzed_last_chat_date TIMESTAMP NULL COMMENT '情感分析时的最后聊天时间',

    -- AI客户画像字段 (有值=已分析)
    persona_summary             TEXT COMMENT '客户画像摘要',
    persona_key_interests       JSON COMMENT '关键兴趣点',
    persona_pain_points         JSON COMMENT '痛点',
    persona_recommended_action  TEXT COMMENT '推荐行动',
    persona_method              VARCHAR(50) COMMENT '分析方法: deepseek/zhipu/rule_based',

    -- 情感/意图分析字段 (有值=已分析)
    sentiment_score             DECIMAL(3,2) COMMENT '情绪分数(0-1)',
    sentiment_label             VARCHAR(20) COMMENT '情绪标签: Positive/Neutral/Negative',
    intent_distribution         JSON COMMENT '意图分布',
    dominant_intent             VARCHAR(50) COMMENT '主要意图',
    pre_sale_keywords           JSON COMMENT '售前关键词',
    post_sale_keywords          JSON COMMENT '售后关键词',
    complaint_count             INT DEFAULT 0 COMMENT '投诉次数',
    sentiment_method            VARCHAR(50) COMMENT '分析方法: zhipu/rule_based',

    -- 元数据
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- 索引
    INDEX idx_persona_analyzed_at (persona_analyzed_at),
    INDEX idx_sentiment_analyzed_at (sentiment_analyzed_at),
    INDEX idx_sentiment_label (sentiment_label),
    INDEX idx_dominant_intent (dominant_intent)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI分析缓存表 - 重构版v2.1';
```

#### 3.1.2 字段分组说明

```
buyer_ai_analysis_cache
│
├── ── 画像分析独立时间戳 ──
│   ├── persona_analyzed_at              -- 画像分析完成时间
│   ├── persona_analyzed_last_purchase_date  -- 画像分析时的最后订单时间
│   └── persona_analyzed_last_chat_date  -- 画像分析时的最后聊天时间
│
├── ── 情感分析独立时间戳 ──
│   ├── sentiment_analyzed_at            -- 情感分析完成时间
│   └── sentiment_analyzed_last_chat_date -- 情感分析时的最后聊天时间
│
├── ── AI客户画像 (persona_* 前缀) ──
│   ├── persona_summary                  -- 有值 = 已分析过画像
│   ├── persona_key_interests
│   ├── persona_pain_points
│   ├── persona_recommended_action
│   └── persona_method
│
├── ── 情感/意图 (sentiment_* 等字段) ──
│   ├── sentiment_score                  -- 有值 = 已分析过情感
│   ├── sentiment_label
│   ├── intent_distribution
│   ├── dominant_intent
│   └── sentiment_method
│
└── ── 元数据 ──
    ├── created_at
    └── updated_at
```

**关键设计点**：两种分析有独立的时间戳和数据快照，可以分别判断是否需要更新。

### 3.2 增量更新判断逻辑

#### 3.2.1 核心原理

```
增量判断原理:
│
├── 画像分析
│   └── 存储独立快照: persona_analyzed_last_purchase_date, persona_analyzed_last_chat_date
│   └── 判断: current.last_purchase_date > persona_analyzed_last_purchase_date
│   └── 判断: current.last_chat_date > persona_analyzed_last_chat_date
│
└── 情感分析
    └── 存储独立快照: sentiment_analyzed_last_chat_date
    └── 判断: current.last_chat_date > sentiment_analyzed_last_chat_date
```

#### 3.2.2 AI客户画像分析触发条件

```python
def should_update_persona(buyer_nick: str, current: dict) -> bool:
    """
    判断是否需要更新AI客户画像

    触发条件 (满足任一):
    1. 从未分析过 (缓存不存在或 persona_summary 为空)
    2. 有新增订单 (last_purchase_date > analyzed_last_purchase_date)
    3. 有新增聊天记录 (last_chat_date > analyzed_last_chat_date)
    """
    cache = get_cache(buyer_nick)

    if not cache or not cache.get("persona_summary"):
        return True  # 首次分析

    # 有新订单？
    current_last_purchase = current.get("last_purchase_date")
    cached_last_purchase = cache.get("analyzed_last_purchase_date")
    if current_last_purchase and cached_last_purchase:
        if current_last_purchase > cached_last_purchase:
            return True

    # 有新聊天？
    current_last_chat = current.get("last_chat_date")
    cached_last_chat = cache.get("analyzed_last_chat_date")
    if current_last_chat and cached_last_chat:
        if current_last_chat > cached_last_chat:
            return True

    return False
```

#### 3.2.3 情感/意图分析触发条件

```python
def should_update_sentiment(buyer_nick: str, current: dict) -> bool:
    """
    判断是否需要更新情感/意图分析

    前提条件: 聊天天数 >= 10

    触发条件 (满足任一):
    1. 从未分析过 (缓存不存在或 sentiment_score 为空)
    2. 有新增聊天记录 (last_chat_date > analyzed_last_chat_date)
    """
    # 前提条件: 聊天天数不足10天，不分析
    if current.get("chat_frequency_days", 0) < 10:
        return False

    cache = get_cache(buyer_nick)

    if not cache or cache.get("sentiment_score") is None:
        return True  # 首次分析

    # 有新聊天？
    current_last_chat = current.get("last_chat_date")
    cached_last_chat = cache.get("analyzed_last_chat_date")
    if current_last_chat and cached_last_chat:
        if current_last_chat > cached_last_chat:
            return True

    return False
```

#### 3.2.4 聊天阈值判断时机

```
判断时机:
│
├─ 批量分析任务启动时 (batch_analyzer.py)
│   └─ 查询: SELECT ... WHERE chat_frequency_days >= 10
│   └─ 只有满足条件的客户才会被加入分析队列
│
└─ 单客户手动触发时 (API请求)
    └─ 先检查 chat_frequency_days >= 10
    └─ 不满足则返回: {"message": "聊天记录不足10天，暂不需要情感分析"}
```

### 3.3 数据流架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        数据更新流程                                   │
└─────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │  订单/聊天数据更新 │
                    └────────┬─────────┘
                             │
                             ▼
        ┌────────────────────────────────────────┐
        │  refresh_target_buyers_precomputed()   │
        │  (每天14:00 定时执行)                   │
        └────────────────┬───────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
    ┌──────────┐  ┌──────────┐  ┌──────────────┐
    │ 计算RFM  │  │ 读取AI   │  │ 更新派生字段  │
    │ 分数     │  │ 缓存数据 │  │ (churn_risk) │
    └──────────┘  └────┬─────┘  └──────────────┘
                       │
                       ▼
              ┌────────────────┐
              │ 从缓存表读取:   │
              │ - sentiment_*  │
              │ - dominant_*   │
              │ (如果存在)     │
              └────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                        AI分析触发流程                                │
└─────────────────────────────────────────────────────────────────────┘

  前端请求                 批量任务
      │                       │
      ▼                       ▼
┌──────────────┐      ┌──────────────┐
│ 单客户画像   │      │ 批量情感分析  │
│ API请求      │      │ 定时任务      │
└──────┬───────┘      └──────┬───────┘
       │                     │
       ▼                     ▼
┌──────────────────────────────────────┐
│          判断是否需要更新             │
│  ┌─────────────┬─────────────────┐   │
│  │ 客户画像:   │ 情感分析:        │   │
│  │ - 首次?     │ - 聊天≥10天?     │   │
│  │ - 新订单?   │ - 首次?          │   │
│  │ - 新聊天?   │ - 新聊天?        │   │
│  └─────────────┴─────────────────┘   │
│                                      │
│  比较: current.last_xxx > cache.analyzed_last_xxx
└──────────────┬───────────────────────┘
               │
               ▼
        ┌──────────────┐
        │ 执行AI分析   │
        │ (多级降级)   │
        └──────┬───────┘
               │
               ▼
        ┌──────────────┐
        │ 存储到缓存表  │
        │ + 更新快照    │
        │ analyzed_*   │
        └──────────────┘
```

### 3.4 手动强制刷新API

```python
# 端点: POST /api/v2/buyers/{buyer_nick}/force-refresh
# 用于异常情况下强制重新分析

@router.post("/buyers/{buyer_nick}/force-refresh")
async def force_refresh(
    buyer_nick: str,
    refresh_type: str = "all"  # "persona" | "sentiment" | "all"
):
    """
    强制刷新AI分析结果

    使用场景:
    - AI返回了错误结果
    - 分析逻辑升级后需要重新分析
    """
    # 清除对应的缓存字段，触发重新分析
    if refresh_type in ["persona", "all"]:
        clear_persona_cache(buyer_nick)
    if refresh_type in ["sentiment", "all"]:
        clear_sentiment_cache(buyer_nick)

    # 触发重新分析
    return {"message": f"已触发 {refresh_type} 重新分析"}
```

---

## 4. 存储过程更新

### 4.1 修改 `refresh_target_buyers_precomputed`

在RFM计算完成后，添加从缓存表读取AI分析结果的逻辑：

```sql
-- ============================================
-- 同步AI分析结果 (情感/意图)
-- ============================================

-- 从缓存表读取情感/意图分析结果
UPDATE target_buyers_precomputed tb
INNER JOIN buyer_ai_analysis_cache cache
    ON tb.buyer_nick = cache.buyer_nick
SET
    tb.sentiment_label = cache.sentiment_label,
    tb.sentiment_score = cache.sentiment_score,
    tb.dominant_intent = cache.dominant_intent
WHERE cache.sentiment_score IS NOT NULL;

SELECT CONCAT('📊 同步了 ', ROW_COUNT(), ' 条AI分析结果') AS message;
```

### 4.2 存储过程更新位置

在现有存储过程中，将新的同步逻辑插入到 **RFM计算之后**、**清理临时表之前**：

```
现有流程:
... → RFM计算 → Follow Priority → [NEW: 同步AI结果] → 清理临时表 → 完成
```

---

## 5. 代码修改清单

### 5.1 需要修改的文件

| 文件 | 修改内容 | 优先级 |
|------|----------|--------|
| `backend/database/sql/ai_cache_refactor.sql` | [NEW] 缓存表结构迁移脚本 | 高 |
| `backend/database/sql/refresh_target_buyers_precomputed_procedure.sql` | 添加AI结果同步逻辑 | 高 |
| `backend/ai/analyzer_orchestrator.py` | 添加数据快照存储，修改增量判断 | 高 |
| `backend/ai/batch_analyzer.py` | 添加数据快照存储，修改增量判断，聊天≥10天判断 | 高 |
| `backend/api/target_routes.py` | 添加强制刷新API | 中 |

### 5.2 删除的字段/逻辑

| 删除项 | 原因 |
|--------|------|
| `cache_key` 字段 | 不再需要，用 buyer_nick 作为主键 |
| `analysis_type` 字段 | 不再需要，一个客户一条记录 |
| `expires_at` 字段 | 删除TTL机制，纯增量更新 |
| `data_fingerprint` 字段 | 用时间戳快照代替 |

---

## 6. 迁移计划

### 6.1 迁移步骤

```bash
# Step 1: 备份现有数据
mysqldump -u user -p dunhill buyer_ai_analysis_cache > cache_backup_$(date +%Y%m%d).sql

# Step 2: 执行迁移脚本
python backend/database/run_migration.py --file backend/database/sql/ai_cache_refactor.sql

# Step 3: 更新存储过程
# - 应用新的 refresh_target_buyers_precomputed

# Step 4: 验证
python backend/database/run_migration.py --check
```

### 6.2 数据迁移SQL

```sql
-- ============================================
-- Step 1: 添加新字段
-- ============================================

ALTER TABLE buyer_ai_analysis_cache
ADD COLUMN analyzed_last_purchase_date TIMESTAMP NULL
    COMMENT '分析时的最后订单时间',
ADD COLUMN analyzed_last_chat_date TIMESTAMP NULL
    COMMENT '分析时的最后聊天时间';

-- ============================================
-- Step 2: 重命名画像字段 (添加 persona_ 前缀)
-- ============================================

ALTER TABLE buyer_ai_analysis_cache
CHANGE COLUMN summary persona_summary TEXT,
CHANGE COLUMN key_interests persona_key_interests JSON,
CHANGE COLUMN pain_points persona_pain_points JSON,
CHANGE COLUMN recommended_action persona_recommended_action TEXT,
CHANGE COLUMN analysis_method persona_method VARCHAR(50);

-- ============================================
-- Step 3: 删除不需要的字段
-- ============================================

ALTER TABLE buyer_ai_analysis_cache
DROP COLUMN cache_key,
DROP COLUMN analysis_type,
DROP COLUMN data_fingerprint,
DROP COLUMN expires_at,
DROP INDEX idx_cache_key,
DROP INDEX idx_buyer_type,
DROP INDEX idx_expires_at;

-- ============================================
-- Step 4: 修改主键 (如果当前不是 buyer_nick)
-- ============================================

-- 先检查当前主键
-- 如果是 id，需要删除并改用 buyer_nick

-- 备选方案：如果表结构复杂，建议重建表
-- CREATE TABLE buyer_ai_analysis_cache_new AS ...
-- RENAME TABLE buyer_ai_analysis_cache TO buyer_ai_analysis_cache_old,
--              buyer_ai_analysis_cache_new TO buyer_ai_analysis_cache;

-- ============================================
-- Step 5: 从 target_buyers_precomputed 补充数据快照
-- ============================================

UPDATE buyer_ai_analysis_cache cache
INNER JOIN target_buyers_precomputed tb ON cache.buyer_nick = tb.buyer_nick
SET
    cache.analyzed_last_purchase_date = tb.last_purchase_date,
    cache.analyzed_last_chat_date = tb.last_chat_date,
    cache.analyzed_at = COALESCE(cache.analyzed_at, cache.created_at);
```

### 6.3 回滚方案

```sql
-- 从备份恢复
SOURCE cache_backup_YYYYMMDD.sql;
```

---

## 7. 测试验证

### 7.1 功能测试

| 测试项 | 验证方法 | 预期结果 |
|--------|----------|----------|
| 画像首次分析 | 查询无缓存客户 | 触发API调用 |
| 画像增量更新 | 模拟新订单/新聊天 | 触发API调用 |
| 画像无变化 | 无新订单/新聊天 | 跳过，使用缓存 |
| 情感首次分析 | 查询聊天≥10天无缓存客户 | 触发API调用 |
| 情感门槛检查 | 查询聊天<10天客户 | 不触发分析 |
| 情感增量更新 | 模拟新聊天 | 触发API调用 |
| 存储过程同步 | 执行刷新后检查 | 情感/意图字段有值 |
| 强制刷新API | 调用force-refresh | 清除缓存并重新分析 |

### 7.2 API测试

```bash
# 测试单客户画像分析
curl "http://localhost:8000/api/v2/buyers/张三/ai-profile"

# 测试批量情感分析
curl -X POST "http://localhost:8000/api/v2/ai/batch-analyze"

# 测试强制刷新
curl -X POST "http://localhost:8000/api/v2/buyers/张三/force-refresh?refresh_type=all"
```

### 7.3 数据验证SQL

```sql
-- 检查缓存表结构
DESCRIBE buyer_ai_analysis_cache;

-- 检查数据快照是否正确填充
SELECT
    buyer_nick,
    analyzed_last_purchase_date,
    analyzed_last_chat_date,
    analyzed_at,
    CASE
        WHEN persona_summary IS NOT NULL THEN '✅ 有画像'
        ELSE '❌ 无画像'
    END as persona_status,
    CASE
        WHEN sentiment_score IS NOT NULL THEN '✅ 有情感'
        ELSE '❌ 无情感'
    END as sentiment_status
FROM buyer_ai_analysis_cache
LIMIT 20;

-- 检查预计算表同步结果
SELECT
    tb.buyer_nick,
    tb.sentiment_label,
    tb.dominant_intent,
    cache.sentiment_score
FROM target_buyers_precomputed tb
LEFT JOIN buyer_ai_analysis_cache cache ON tb.buyer_nick = cache.buyer_nick
WHERE tb.sentiment_label IS NOT NULL
LIMIT 10;

-- 验证增量更新逻辑
-- 查找需要更新的客户（有新订单或新聊天）
SELECT
    tb.buyer_nick,
    tb.last_purchase_date as current_purchase,
    cache.analyzed_last_purchase_date as cached_purchase,
    tb.last_chat_date as current_chat,
    cache.analyzed_last_chat_date as cached_chat,
    CASE
        WHEN tb.last_purchase_date > cache.analyzed_last_purchase_date THEN '📦 有新订单'
        WHEN tb.last_chat_date > cache.analyzed_last_chat_date THEN '💬 有新聊天'
        ELSE '✅ 无需更新'
    END as update_status
FROM target_buyers_precomputed tb
INNER JOIN buyer_ai_analysis_cache cache ON tb.buyer_nick = cache.buyer_nick
LIMIT 20;
```

---

## 附录

### A. 相关文件路径

```
backend/
├── ai/
│   ├── analyzer_orchestrator.py   # AI客户画像分析
│   └── batch_analyzer.py          # 批量情感/意图分析
├── database/
│   └── sql/
│       ├── ai_cache_refactor.sql  # [NEW] 迁移脚本
│       └── refresh_target_buyers_precomputed_procedure.sql
└── api/
    └── target_routes.py           # API端点
```

### B. 变更历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-02-26 | 初始版本 |
| v1.1 | 2026-02-26 | Reader测试反馈修复 |
| v2.0 | 2026-02-26 | **重大变更**：采用方案B（一个客户一条记录），删除TTL机制，纯增量更新 |
