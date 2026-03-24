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

### 2026-03-24
- ✅ **关键词分类优化和统计去重**
  - 移除有包含关系的关键词（长词包含短词 → 只保留短词）
  - 移除歧义关键词（"收到"表示了解不是物流，"要换"不是换货）
  - 实现分类层级去重（同条消息同分类只计1次）
  - 更新 Insight 显示 TOP3 分类和 TOP5 关键词
  - 文档归档到 `docs/plans/2026-03-23-keyword-analysis-*.md`

- ✅ **MetricCards重构 - 运营导向4组指标**（进行中）
  - 设计方向： 从销售数据转向运营决策支持
  - 4个主题组： 客户健康度 / 跟进优先级 / 销售机会 / 服务质量
  - 每组2-3个指标，带占比显示
  - 文件: `src/components/dashboard/MetricCards.tsx`

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
