# Task Plan: SMOKER客户关键词词云分析功能

## Goal
开发客户聊天记录关键词分析功能，展示客户关注点和反馈的词云分布，帮助运营团队了解客户需求。

## Current Phase
Phase 5

## Phases

### Phase 1: 后端数据层
- [x] 创建关键词分类词典（9个大类）
- [x] 创建缓存表 `keyword_analysis_cache`
- [x] 实现关键词提取和分类逻辑
- [x] 编写预计算脚本（每日更新）
- **Status:** complete

### Phase 2: 后端API层
- [x] 创建 `/api/v2/keyword-analysis` API
- [x] 支持客户类型多选筛选（ALL/SMOKER/BOTH/VIC/NON_SMOKER_VIC）
- [x] 支持分类筛选
- [x] 返回分类分布 + 关键词排行数据
- **Status:** complete

### Phase 3: 前端组件重构
- [x] 重构 `KeywordAnalysisPanel.tsx`
- [x] 左侧：甜甜圈图显示9个大类分布
- [x] 右侧：水平柱状图显示TOP关键词（绝对值+占比）
- [x] 客户类型多选筛选器
- [x] 分类点击联动
- **Status:** complete

### Phase 4: 集成测试
- [x] 前后端联调
- [x] 验证筛选逻辑
- [x] 验证数据准确性
- **Status:** complete

### Phase 5: 清理与交付
- [x] 删除占位数据
- [x] 更新文档
- [x] 移除 NON_SMOKER_VIC（只保留 ALL/SMOKER/BOTH/VIC）
- [x] 重构前端组件使用 Notion 简约风格
- **Status:** complete

## Key Questions
1. ✅ 分类体系：9个大类（赠品、包装、维修保养、退换货、产品推荐咨询、产品参数咨询、价格、物流、投诉反馈）
2. ✅ 数据来源：客户消息（sender_nick = user_nick）
3. ✅ 计算方式：预计算+缓存
4. ✅ UI布局：左侧甜甜圈图 + 右侧柱状图
5. ✅ 筛选器：客户类型多选 + 分类单选

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 预计算+缓存 | 聊天记录量大，实时分析响应慢 |
| 9个大类 | 基于真实数据分析，覆盖主要场景 |
| 动态展示子类 | 数据量有限，不预定义小类，让数据说话 |
| 水平柱状图 | 清晰展示关键词排行，易于比较 |
| 左右分栏布局 | 复用现有组件结构，降低开发成本 |

## Technical Design

### 9个分类及关键词
| 分类 | 关键词 |
|------|--------|
| 赠品 | 赠品、礼品、送、小样 |
| 包装 | 包装、礼盒、袋子 |
| 维修保养 | 维修、保养、清洗、售后 |
| 退换货 | 退货、换货、退款 |
| 产品推荐咨询 | 推荐、哪个好、怎么选、适合 |
| 产品参数咨询 | 尺寸、口径、规格、直径 |
| 价格 | 价格、优惠、折扣、活动 |
| 物流 | 发货、快递、到货、顺丰 |
| 投诉反馈 | 投诉、差评、不满意、态度、质量问题 |

### API Design
```
GET /api/v2/keyword-analysis
Query Params:
  - buyer_types: string (comma-separated, e.g., "SMOKER,BOTH")
  - category: string (optional, filter by category)

Response:
{
  "category_distribution": [
    { "name": "赠品", "value": 112, "percentage": 10.1 },
    ...
  ],
  "keywords": [
    { "text": "赠品", "value": 45, "percentage": 23.1, "category": "赠品" },
    ...
  ],
  "total_messages": 1110
}
```

### 数据库表设计
```sql
CREATE TABLE keyword_analysis_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    buyer_type ENUM('ALL', 'SMOKER', 'BOTH', 'VIC', 'NON_SMOKER_VIC'),
    category VARCHAR(50),
    keyword VARCHAR(100),
    count INT,
    percentage DECIMAL(5,2),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_buyer_category (buyer_type, category)
);
```

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
|       | 1       |            |

## Notes
- 更新 phase status: pending → in_progress → complete
- 每次完成 phase 后更新此文件
- 记录所有错误以便复盘
