# 流失预警对比周期可配置 (CRM Round 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 把流失预警的"对比周期"从硬编码 30 天改成 60/90/180 三档可切换（默认 90），后端加 window 参数 + 阈值表，前端加分段控件 + 阈值文字提示。

**Architecture:** 单向数据流 — Tab 2 头部右侧 `60D/90D/180D` 分段控件 -> `useState<60|90|180>` -> `apiClient.getChurnWarning({window})` -> 后端路由 `target_routes.get_churn_warning_list` 校验 + 查阈值表 -> `analyzer.get_churn_warning(window_days, l6m_floor)` -> `queries.get_churn_warning` -> SQL 接收 `:window_days` 和 `:l6m_floor` 命名参数。

**Tech Stack:** Python 3.13 (FastAPI) / MySQL (pymysql) / React 19 + TypeScript + Vite

**Note on TDD:** 本项目**没有自动化测试基础设施**（无 `tests/` 目录，无 pytest，无 vitest），历史 commit（Round 1/2）也均用 curl + 浏览器手动验证。本 plan 沿用同款手动验证策略。

---

## File Structure

**修改 (6 个文件)**：

| 文件 | 职责 |
|---|---|
| `backend/database/sql/target_buyers/get_churn_warning.sql` | 把 `INTERVAL 30 DAY` 改成 `INTERVAL :window_days DAY`；`_cond_c` 基线 10000 改成 `:l6m_floor` |
| `backend/database/target_buyer_queries.py` | `get_churn_warning(limit, offset, window_days, l6m_floor)` 透传命名参数 |
| `backend/analytics/target_buyer_analyzer.py` | `get_churn_warning(limit, offset, window_days, l6m_floor)` 透传 |
| `backend/api/target_routes.py` | route 加 `window: int = Query(90)` 参数 + 校验 + 阈值表 + 包装 SQL 参数 |
| `src/api/client.ts` | `ChurnWarningRow` 字段重命名 + 新 `ChurnWarningResponse` 类型 + `getChurnWarning(opts)` 签名 |
| `src/components/dashboard/PriorityAttentionBoard.tsx` | `useState<60|90|180>(90)` + Tab 2 头部右侧分段控件 + 阈值文字提示 + 字段名适配 |

**不变**：所有其他 API、所有其他前端组件、history snapshot 调度、预计算表结构。

---
