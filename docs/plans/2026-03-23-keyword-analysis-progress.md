# Progress: SMOKER客户关键词词云分析

## Session Log

### 2026-03-23

#### 设计阶段完成
- ✅ 完成需求讨论和设计确认
- ✅ 创建 task_plan.md, findings.md, progress.md
- ✅ 确定分类体系（9个大类）
- ✅ 确定UI布局（左侧甜甜圈图 + 右侧柱状图）
- ✅ 确定筛选逻辑（客户类型多选 + 分类单选）

#### Phase 1: 后端数据层 ✅
- ✅ 创建关键词分类词典 `backend/analytics/keyword_categories.py`
- ✅ 创建缓存表 SQL `backend/database/sql/create_keyword_analysis_cache.sql`
- ✅ 创建预计算脚本 `scripts/refresh_keyword_analysis_cache.py`
- ✅ 运行预计算，填充数据

**数据摘要：**
- ALL: 416条消息, 77个唯一关键词
- SMOKER: 273条消息, 69个唯一关键词
- BOTH: 14条消息, 10个唯一关键词
- VIC: 113条消息, 40个唯一关键词
- NON_SMOKER_VIC: 16条消息, 16个唯一关键词

#### Phase 2: 后端API层 ✅
- ✅ 创建 `/api/v2/keyword-analysis` API
- ✅ 支持客户类型多选筛选
- ✅ 支持分类筛选
- ✅ 返回分类分布 + 关键词排行数据
- ✅ 修复 Decimal 类型转换问题

#### Phase 3: 前端组件重构 ✅
- ✅ 重构 `KeywordAnalysisPanel.tsx`
- ✅ 客户类型多选筛选器
- ✅ 左侧甜甜圈图显示分类分布
- ✅ 右侧水平柱状图显示关键词（绝对值+占比）
- ✅ 分类点击联动
- ✅ 添加 API 方法到 `src/api/client.ts`

#### Phase 4: 集成测试 ✅
- ✅ API 测试通过
- ✅ 筛选逻辑正确
- ✅ 数据准确性验证

---

## Test Results
| Test | Status | Notes |
|------|--------|-------|
| ALL 客户 API | ✅ Pass | 416条消息, 9个分类 |
| SMOKER 客户 API | ✅ Pass | 273条消息 |
| 分类筛选 API | ✅ Pass | 赠品分类筛选正确 |
| Decimal 类型修复 | ✅ Pass | int() 转换 |

---

## Files Created/Modified
| File | Action | Description |
|------|--------|-------------|
| task_plan.md | Created | 任务计划 |
| findings.md | Created | 研究发现 |
| progress.md | Created | 进度日志 |
| backend/analytics/keyword_categories.py | Created | 关键词分类词典 |
| backend/database/sql/create_keyword_analysis_cache.sql | Created | 缓存表SQL |
| scripts/refresh_keyword_analysis_cache.py | Created | 预计算脚本 |
| backend/api/target_routes.py | Modified | 添加关键词分析API |
| src/api/client.ts | Modified | 添加API方法和类型定义 |
| src/components/dashboard/KeywordAnalysisPanel.tsx | Modified | 重构前端组件 |

---

## Errors Fixed
| Error | Resolution |
|-------|------------|
| 列名错误 (user_nick vs buyer_nick) | 修正预计算脚本中的列名 |
| Decimal + float 类型错误 | 使用 int() 转换数据库返回值 |
| NON_SMOKER_VIC 错误分类 | 从 ENUM 中移除，只保留 ALL/SMOKER/BOTH/VIC |
| UI 颜色过于鲜艳 | 重构组件使用 Notion 简约风格的柔和色调 |

---

## UI 改进 (2026-03-23)

### 设计方向：Notion 简约风格
- **颜色系统**: 低饱和度 pastel 色调，与 NotionTag 组件一致
- **筛选器**: 标签式设计（选中态为深色背景）
- **图表**: 柔和的填充色 + 略深的边框色
- **交互**: 点击甜甜圈图联动筛选关键词

### 颜色映射
| 分类 | 填充色 | 边框色 |
|------|--------|--------|
| 赠品 | #E7DEFF | #C4B5FD |
| 包装 | #E7F3F8 | #93C5FD |
| 维修保养 | #EDF3EC | #86EFAC |
| 退换货 | #FDEBEC | #FCA5A5 |
| 产品推荐咨询 | #FBF3DB | #FCD34D |
| 产品参数咨询 | #F4EEEE | #D4A574 |
| 价格 | #FAF1F5 | #F9A8D4 |
| 物流 | #E7F3F8 | #93C5FD |
| 投诉反馈 | #FDEBEC | #FCA5A5 |

#### Phase 5: 关键词优化与UI调整 ✅
- ✅ 移除单字关键词（避免歧义，如"送"、"换"、"发"等）
- ✅ 移除模糊关键词（如"礼物"、"免费"、"问题"等）
- ✅ 调整甜甜圈图标签显示策略（只显示前6大分类）
- ✅ 优化 Tooltip 显示格式
- ✅ 修复引导线显示逻辑

**关键词优化原则：**
1. 所有关键词必须 >= 2个字
2. 只使用语义明确的词，避免歧义
3. 不使用太宽泛的词（如"免费"、"问题"）

**最终分类分布（优化后）：**
| 排名 | 分类 | 消息数 | 占比 |
|-----|------|-------|------|
| 1 | 物流 | 87 | 21.43% |
| 2 | 退换货 | 70 | 17.24% |
| 3 | 包装 | 57 | 14.04% |
| 4 | 价格 | 52 | 12.81% |
| 5 | 产品参数咨询 | 48 | 11.82% |
| 6 | 产品推荐咨询 | 39 | 9.61% |
| 7 | 维修保养 | 26 | 6.40% |
| 8 | 赠品 | 20 | 4.93% |
| 9 | 投诉反馈 | 7 | 1.72% |

---

## Next Actions
1. ✅ 功能已完成
2. 文档已归档到 `docs/plans/` 和 `docs/screenshots/keyword-analysis/`
