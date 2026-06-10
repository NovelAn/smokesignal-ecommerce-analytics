# Backfill: target_buyers_precomputed_history

一次性脚本, 把 2025-04-01 起每天 d 的真 ASOF 状态写入历史快照表。

## 概述

- **存储过程**: `backend/database/sql/procedures/refresh_target_buyers_asof.sql`
  - 输入参数: `IN p_asof_date DATE`
  - 行为: 与 `snapshot_target_buyers_history()` 算法完全一致, 仅日期源不同
  - 幂等: `ON DUPLICATE KEY UPDATE`, 重跑不重复
- **Python 脚本**: `scripts/backfill_target_buyers_history.py`
- **目标表**: `target_buyers_precomputed_history` (PR1 已创建)
- **数据源**: `dunhill_t01_trade_line` (订单宽表 VIEW)
- **默认范围**: 2025-04-01 → 昨天 (T-1, 与主表 procedure 一致)
- **总耗时**: 预计 14M 累积 / 730 万行, 单日 < 1s, 全部 ~15-30 分钟

## 前置条件

1. **PR1 已 merge 到 main** ✅
2. **生产库 procedure 已部署**:
   ```bash
   mysql -u$USER -p$PASS dunhill < backend/database/sql/procedures/refresh_target_buyers_asof.sql
   ```
3. **目标表已存在** (PR1 DDL):
   ```sql
   SHOW TABLES LIKE 'target_buyers_precomputed_history';
   ```
4. **DB 配置** `~/database_config.json` 存在 (项目惯例)

## 用法

### 1. 干跑 (推荐先跑一次确认计划)

```bash
PYTHONPATH=. python scripts/backfill_target_buyers_history.py --dry-run
```

输出: 列出所有待跑日期 + 范围信息, 不写库。

### 2. 自定义范围

```bash
PYTHONPATH=. python scripts/backfill_target_buyers_history.py \
    --start 2025-04-01 \
    --end 2025-04-30 \
    --dry-run
```

### 3. 正式跑 (默认避峰 02:00-06:00)

```bash
# 凌晨 02:00 起跑, 让脚本自己跑
PYTHONPATH=. python scripts/backfill_target_buyers_history.py
```

### 4. 白天调试 (绕过避峰)

```bash
PYTHONPATH=. python scripts/backfill_target_buyers_history.py --force
```

### 5. 断点续跑

```bash
# 中断后直接重跑, 脚本自动从进度文件恢复
PYTHONPATH=. python scripts/backfill_target_buyers_history.py

# 或显式指定 resume 点
PYTHONPATH=. python scripts/backfill_target_buyers_history.py --resume-from 2025-05-15
```

## 进度持久化

进度写到 `logs/backfill_progress.json`, 格式:

```json
{
  "last_success_date": "2025-05-15",
  "failed_dates": ["2025-05-03"],
  "started_at": "2026-06-05T02:00:12",
  "last_updated_at": "2026-06-05T02:23:45",
  "total_success": 45,
  "total_failed": 1
}
```

- `last_success_date`: 最后一天成功写入的日期
- `failed_dates`: 3 次重试后仍失败的日期
- 每次跑完一天立即更新 (中断可恢复)

## 避峰机制

- 默认窗口: **02:00 - 06:00** (与主表 13:20 / snapshot 13:30 错开, 选凌晨是因为:
  - 避开主表 11:00-13:30 重算 + snapshot 窗口
  - 避开客服 8:00-22:00 业务高峰
  - 数据库 IO 压力最低)
- 非窗口期脚本**自动暂停** (写入 last_success_date), `--force` 绕过
- 监控时无需盯窗口, 凌晨跑一次即可

## 失败处理

- **单日重试**: 最多 3 次, 指数退避 5s → 15s → 45s
- **3 次仍失败**: 加入 `failed_dates`, 继续下一天
- **全部跑完**: 日志汇总 failed 列表, 人工检查后单独重跑:
  ```bash
  PYTHONPATH=. python scripts/backfill_target_buyers_history.py --resume-from 2025-05-03
  ```
- **告警**: 不内置 email/钉钉, 失败靠日志 + 进度文件观察

## 验证

跑完后验证:

```sql
-- 总行数 (期望 ~14M * 池子大小 200-300 ≈ 3-5M 行)
SELECT COUNT(*), COUNT(DISTINCT snapshot_date), COUNT(DISTINCT buyer_nick)
FROM target_buyers_precomputed_history;

-- 按月份分区
SELECT PARTITION_NAME, TABLE_ROWS
FROM information_schema.PARTITIONS
WHERE TABLE_NAME = 'target_buyers_precomputed_history'
  AND TABLE_SCHEMA = DATABASE()
ORDER BY PARTITION_ORDINAL_POSITION
LIMIT 5;

-- 池子动态 (期望: 222-260 之间波动, 无突变)
SELECT snapshot_date, COUNT(*)
FROM target_buyers_precomputed_history
GROUP BY snapshot_date
ORDER BY snapshot_date DESC
LIMIT 30;

-- 与 demo 阶段 (2025-04-01 ~ 2025-04-30) 抽样对比
SELECT * FROM target_buyers_precomputed_history
WHERE snapshot_date BETWEEN '2025-04-01' AND '2025-04-30'
  AND buyer_nick IN ('eddendeng', 'laoliu0218', 'tb7235476306')
ORDER BY buyer_nick, snapshot_date;
```

## 监控一周

- 每天 13:30 snapshot 事件后, 确认:
  - 主表 procedure 没失败 (MySQL event log)
  - snapshot 写入正常 (`SELECT MAX(snapshot_date) FROM target_buyers_precomputed_history`)
- 重点关注 2025-04-01 ~ 当天的历史段是否有数据漂移
- 一周后, 启用 PR3 (API) + PR4 (UI)

## 回滚

- **重跑某天**: procedure 幂等, 直接重跑即可
- **删除某天数据**:
  ```sql
  DELETE FROM target_buyers_precomputed_history
  WHERE snapshot_date = '2025-05-15';
  ```
- **整张表重置**:
  ```sql
  TRUNCATE target_buyers_precomputed_history;
  ```
  (注意: partition 不会被删除, 只清数据)

## 与 PR1 / PR3 / PR4 关系

| PR | 状态 | 关系 |
|---|---|---|
| PR1 (schema) | ✅ 已合并 | 提供目标表 + snapshot procedure |
| **PR2 (本脚本)** | ⏳ 进行中 | 历史数据回填, 一次性 |
| PR3 (API) | ⏳ | 依赖 PR2 跑出真实数据 |
| PR4 (UI) | ⏳ | 依赖 PR3 |

## 维护

- procedure 主体逻辑必须与 `snapshot_target_buyers_history()` 保持一致
- 任何算法调整需同步两处 (脚本开头有注释提示)
- 跑完后建议保留本脚本作为"异常补跑工具" (单日重算用)
