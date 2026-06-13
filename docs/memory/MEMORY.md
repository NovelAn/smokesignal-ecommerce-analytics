# SmokeSignal Analytics 项目记忆

## 待开发任务

### 1. Dictionary Management 配置结合
**优先级**: 中

**需求细节**:
- 检查现有 Dictionary Management 配置功能
- 结合SMOKER关键词分析，配置dunhill真实用户/品牌关注的关键词
- 支持关键词分类管理

**待确认**:
- 当前 Dictionary Management 的具体用途和实现状态
- 是否需要扩展为NLP tagging配置

---

### 2. 待测试功能和Bug修复
**优先级**: 中

**待测试**:
- AI画像重新生成功能 (已实现，需验证准确性)
- Intent Distribution雷达图数据准确性
- 缓存增量更新逻辑

**已知问题**:
- AI分析可能产生幻觉，需要验证预计算天数字段是否生效

---

## 已完成功能

### 2026-06-13 (AI 分析优化 Round 4-5)
- ✅ **Round 4: 增量 AI 分析** (3a71e1f)
  - 首次 50 条 / 重刷 20+5=25 条, 后续调到 50+动态
  - helper `fetch_chats_for_analysis(buyer_nick, cache_record, analysis_type)` 统一入口
  - 动态上下文窗口: 增量越少, 历史越多 (n≤3 拿+15历史, n≤9 拿+10, n≤19 拿+5, n≤50 拿+0, n>50 截到50+0)
  - 写回 cache 用 `chats[0].msg_time` (DESC 排序下最新) 而非 `chats[-1]`
  - SQL 已有 `since_msg_time` 支持, 不改 SQL

- ✅ **R5: persona prompt 精简** (677d6a6 + ec39653 + 36fa945)
  - profile 字段 25→11 (砍 4 基础画像前端已有 + 8 冗余聚合 + 1 时间, 保留 rolling_24m VIP 依据)
  - compact_context 截断参数化: full=15000, 增量=8000
  - JSON 顺序重排: chat_insights → recent_chats 在前 (截断优先保留 chat)
  - 复购频率预计算 helper (`首次购买/高频<60天/中频/中低频/低频`), 禁止 LLM 算
  - key_interests 2-4 个短语标签 (2-6字), pain_points 1-3 个短语标签
  - 实测 MiniMax L1 响应 78s→43s

- ✅ **修复 + 防御性**
  - ca69f2b: 修 R5 引入的两个 f-string NameError (MiniMax + DeepSeek 都失败→L3 兜底)
  - 60cfbc8: JSON 顺序 chat_first (116 单客户 chat 数据被 order 膨胀挤掉)
  - 2329f23: 截断参数化 full=15000 / 增量=8000
  - f92204b: incremental_new_limit 20→50 (男装奢品客户 30-50/周很常见)
  - ec3385e: 移除"凑单"标签, 改用中性"同日多件"+"连带率高"
  - bd8b587: 统一 persona prompt 风格 (向 DeepSeek V4 Pro 看齐)
  - 79e4e3c: MiniMax 429 `max_retries=0` 秒降级 L2
  - 2e2178a: Vite proxy timeout 30s→120s (DeepSeek 22s+ 不再误报"AI分析失败")
  - 3c8707e: 增量模式正确读所有新消息 (SQL `LIMIT 200` 兜底, Python 端 `[:50]` 截断)
  - 8589cd4: 动态上下文窗口 (增量越少, 历史越多)

- ✅ **测试**
  - python3 -m py_compile: 0 错误
  - npx tsc --noEmit: 0 错误
  - 用户验证 2 客户画像质量 "还行, 过的去"
  - PR #9 已合并到 main

### 2026-06-12 (CRM Round 2 + Round 3 + 4 bug 修复)
- ✅ **Round 2: 流失预警 3 条件 + 入选原因 UI**
  - SQL: 加 _cond_a_severe / severity_tier (1-4) / selection_reasons / l6m_change_pct
  - 保留 MAX(snapshot_date) 兜底, h_prev COALESCE 到 MIN(snapshot_date)
  - route: GET /api/v2/history/churn-warning (limit/offset/include_total)
  - 字段命名: segment_30d_ago / churn_risk_30d_ago (Round 3 后会重命名为 _prev)

- ✅ **Round 3: 流失预警对比周期可配置 (60D/90D/180D, 默认 90)**
  - 业务背景: 男装奢品客群复购周期 3-6 月, 30D 窗口漏季度性消费降级客户
  - SQL 命名参数化: INTERVAL 30 DAY -> INTERVAL %(window_days)s DAY, l6m_floor 10000 -> %(l6m_floor)s
  - route 加 window 参数 (60/90/180 校验) + 阈值表 (1万/1.5万/2万)
  - 段位退化/churn 升级阈值 3 档统一不变, 只有购买力坍塌基线随档位变
  - 字段重命名: segment_30d_ago -> segment_prev, churn_risk_30d_ago -> churn_risk_prev
  - response 加 window_days + applied_thresholds 字段
  - 前端 PriorityAttentionBoard: useState<60|90|180>(90) + 60D/90D/180D 分段控件 + 阈值动态文字
  - Spec: docs/superpowers/specs/2026-06-12-churn-window-config-design.md
  - Plan: docs/superpowers/plans/2026-06-12-churn-window-config.md

- ✅ **Round 3 后续 4 bug 修复 (commit e57477e)**
  - Bug #1 字段错位: ChurnRowCells 内部多 1 个色条 td 跟 thead 8 列对不上, 改用 border-l-4
  - Bug #2 筛选不生效: churn tab 客户端 filter (后端 churn-warning 不支持 filter, 避免再加 SQL)
  - Bug #3 scroll to 原位: 删 "只 priority tab 触发" gate, 两个 tab 都跑 scroll 逻辑
  - Bug #4 跟进客户 527 全量: use_default_filter 派生 (空 filter -> true, 非空 -> false)
  - TypeScript: 0 错误
  - 端到端: curl 3 档 + 校验 + 默认值全过
### 2026-03-24
- ✅ **关键词分类优化和统计去重**
  - 移除有包含关系的关键词（长词包含短词 → 只保留短词）
  - 移除歧义关键词（"收到"表示了解不是物流，"要换"不是换货）
  - 实现分类层级去重（同条消息同分类只计1次）
  - 更新 Insight 显示 TOP3 分类和 TOP5 关键词
  - 文档归档到 `docs/plans/2026-03-23-keyword-analysis-*.md`

- ✅ **MetricCards重构 - 运营导向4组指标**
  - 设计方向： 从销售数据转向运营决策支持
  - 4个主题组： 客户健康度 / 跟进优先级 / 销售机会 / 服务质量
  - 每组2-3个指标，带占比显示
  - 修复：API返回字符串类型导致的数值计算错误（添加 `toNumber()` 辅助函数）
  - 文件: `src/components/dashboard/MetricCards.tsx`
  - SQL: `backend/database/sql/target_buyers/get_dashboard_metrics.sql`

### 2026-03-23
- ✅ **SMOKER客户关键词词云分析** - Overview页面 Keyword & Issue Analysis 模块
  - 9个分类：赠品、包装、维修保养、退换货、产品推荐咨询、产品参数咨询、价格、物流、投诉反馈
  - 客户类型多选筛选（ALL/SMOKER/BOTH/VIC） - 注意：移除了 NON_SMOKER_VIC
  - 左侧甜甜圈图显示分类分布（只显示前6大分类标签，其他通过hover查看）
  - 右侧水平柱状图显示TOP关键词（绝对值+占比）
  - 分类点击联动
  - UI 采用 Notion 简约风格（低饱和度 pastel 色调）
  - 预计算缓存表：keyword_analysis_cache, category_distribution_cache, keyword_analysis_meta
  - API: GET /api/v2/keyword-analysis

### 2026-03-20
- ✅ Priority Attention Board (近期需关注客户表单) - 可导出的客户跟进表单

### 2026-03-18
- ✅ Intent Distribution从后端缓存获取并正确解析JSON
- ✅ AI Persona缓存逻辑修复 (toggle不再清除缓存)
- ✅ 预计算天数字段 (days_since_last_purchase, days_since_last_chat, avg_repurchase_interval_days)
- ✅ churn_risk SQL逻辑修复 (中风险从OR改为AND)
- ✅ Single Customer Analysis添加"重新生成画像"按钮
- ✅ Prompt优化，强调使用预计算值

---

## 技术栈备注

- **前端**: React 19 + TypeScript + Vite + Recharts
- **后端**: FastAPI + MySQL
- **AI**: DeepSeek-R1 (主) + Zhipu GLM-4 (备) + Rule-based (最终降级)
- **缓存策略**: 增量更新，无TTL，基于数据快照判断是否需要重新分析

---

## 关键词分析模块技术细节

### 文件结构
- `backend/analytics/keyword_categories.py` - 9个分类的关键词词典
- `backend/database/sql/create_keyword_analysis_cache.sql` - 缓存表DDL
- `scripts/refresh_keyword_analysis_cache.py` - 预计算脚本（每日更新）
- `backend/api/target_routes.py` - `/api/v2/keyword-analysis` API
- `src/components/dashboard/KeywordAnalysisPanel.tsx` - 前端组件

### 关键词设计原则
1. 所有关键词必须 >= 2个字（避免单字歧义）
2. 移除有包含关系的关键词（长词包含短词 → 只保留短词）
3. 移除歧义关键词（如"收到"表示了解，不是物流）
4. 只使用语义明确、不易产生歧义的关键词

### 统计逻辑
- **分类层级**：每条消息每个分类只计1次（去重）
- **关键词层级**：可分别计数（用于了解具体表达方式）

### 9个分类及关键词（优化后）
| 分类 | 关键词 |
|------|--------|
| 赠品 | 赠品、小样、试用装、满赠、满送、有赠吗 |
| 包装 | 包装、礼盒、袋子、礼袋、礼品袋、手提袋、有盒子、送人用 |
| 维修保养 | 维修、保养、清洗、清洁、售后、修理、维护、坏了、损坏、保修、故障、不能用了 |
| 退换货 | 退货、换货、退款、退换、退回、换一个、退了、换一下、想换、换个 |
| 产品推荐咨询 | 推荐、哪个好、怎么选、适合、介绍、有什么区别、建议、款式、哪款、帮我选 |
| 产品参数咨询 | 尺寸、大小、口径、规格、直径、长度、高度、宽度、重量、参数、多大、多重、多长、多少目 |
| 价格 | 价格、多少钱、优惠、折扣、便宜、活动、促销、满减、会员价、打折、降价、差价 |
| 物流 | 发货、快递、物流、顺丰、到货、什么时候到、配送、运单、什么时候发、几天到、多久到 |
| 投诉反馈 | 投诉、差评、质量问题、瑕疵、缺陷、做工、粗糙、服务差、质量差、很失望、太慢了、态度差 |

### 数据刷新
运行命令: `PYTHONPATH=. python scripts/refresh_keyword_analysis_cache.py`

---

## 运维踩坑

### 启动后端的正确姿势
- 项目自带 `.venv/` 在项目根（已装 fastapi / uvicorn 等）
- ✅ 脚本: `./scripts/start-backend.sh`（main 分支已修，feature 分支未带此修复）
- ✅ 手动: `./.venv/bin/python -m backend.main`（最稳）
- ❌ 避免: `python -m backend.main` —— 当前 `which python` 指向 `/Users/novel/Projects/data-import/.venv/bin/python`（**别项目的 venv 漏到了 PATH**）
- 端口 8000 被旧进程占着时，新进程会 `address already in use` 直接退出；先 `lsof -i :8000` 查 PID

### PATH 污染（用户级，非项目级）
- 现象: `which python` / `which python3` 都返回 `data-import/.venv/bin/python`
- 根因: 之前在 `data-import` 项目 `source` 过 venv，PATH 残留
- 定位: `grep -nE "data-import|venv|VIRTUAL_ENV" ~/.zshenv ~/.zprofile ~/.zshrc`
- 修复: 删掉写入 PATH 的那行，删掉后 `source ~/.zshrc` 或重开终端
