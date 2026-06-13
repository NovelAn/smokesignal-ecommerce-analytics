# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SmokeSignal Analytics is a Notion-style CRM dashboard for luxury e-commerce customer service analytics. It visualizes customer sentiment, chat history, purchase behavior, and AI-powered customer insights for Taobao/Tmall operations (specifically dunhill China).

**Tech Stack:**

- **Frontend**: React 19 + TypeScript + Vite 6 + Recharts 3.6
- **Backend**: FastAPI (Python) + MySQL 8.0+
- **AI**: 3-tier intelligent routing (MiniMax M3 → DeepSeek V4 Pro/Flash → Rule-based) with 84% cost savings
- **Data Source**: Playwright-based crawler from Qianniu Workbench

## Common Development Commands

### Frontend Development

```bash
# Install dependencies
npm install

# Start dev server (http://localhost:3000)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Backend Development

```bash
# Start backend server (http://localhost:8000)
./scripts/start-backend.sh  # Linux/Mac
scripts\start-backend.bat   # Windows

# Or directly with Python
python -m backend.main

# Run with uvicorn
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing

```bash
# Run all tests
python tests/run_all_tests.py

# Run specific test categories
python tests/api/test_api_endpoints.py
python tests/database/test_db_connection.py
python tests/integration/test_api_integration.py
```

### Database Operations

```bash
# Deploy target buyers precomputed table (creates table, stored procedures, events, partitions)
./scripts/deploy_mysql.sh  # Linux/Mac
# Note: Update database credentials in the script first

# Manual refresh of precomputed data
mysql -u username -p database_name -e "CALL refresh_target_buyers_asof(CURDATE());"

# Create daily snapshot
mysql -u username -p database_name -e "CALL snapshot_target_buyers_history();"
```

## Architecture

### Data Flow

```
Qianniu Workbench (Taobao/Tmall)
    ↓
Playwright Crawler (chat-history-crawler project)
    ↓
MySQL Database (dunhill_t01_trade_line VIEW, chat_history table)
    ↓
FastAPI Backend (Target Buyer Analysis + AI Persona + Keyword Analysis)
    ↓
React Frontend (Dashboard Overview + Chat & CRM + Configuration)
```

### Backend Architecture

**API Structure:**

All production APIs use `/api/v2/*` prefix (v1 deprecated):

- `/api/v2/buyers/*` - Customer profiles, lists, filtering
- `/api/v2/dashboard/*` - Metrics, trends, YoY comparison
- `/api/v2/ai/*` - Persona analysis, sentiment/intent, batch operations
- `/api/v2/history/*` - Time-series trends (pool summary, segment trends, VIP trends)
- `/api/v2/priority-customers` - CRM actionable list (churn warning + high-value opportunities)
- `/api/v2/keyword-analysis` - 9-category keyword aggregation for SMOKER customers
- `/api/v2/external/*` - Offline consumption and private domain communication tracking

**Key Backend Components:**

- `backend/api/target_routes.py` - Main API routes (2,683 lines)
- `backend/api/external_routes.py` - External records API
- `backend/analytics/target_buyer_analyzer.py` - Customer analytics engine (precomputed table)
- `backend/analytics/keyword_categories.py` - 9-category keyword taxonomy
- `backend/database/target_buyer_queries.py` - SQL query loader (loads from .sql files)
- `backend/ai/analyzer_orchestrator.py` - Multi-model orchestration with fallback
- `backend/ai/model_selection.py` - Intelligent model routing (complexity scoring)
- `backend/ai/minimax_client.py` - MiniMax M3 client (L1 - primary)
- `backend/ai/deepseek_client.py` - DeepSeek V4 Pro/Flash client (L2 - backup)
- `backend/ai/rule_based_analyzer.py` - Rule-based fallback (L3)

### AI Model Architecture

**3-Tier Intelligent Routing with Cost Optimization:**

```
┌─────────────────────────────────────────────────────────────┐
│  L1: MiniMax-M3 (Primary - Monthly Subscription)           │
│  • All persona analysis attempts start here                 │
│  • ¥0 per call (unlimited within plan)                      │
│  • max_retries=0 for fast fallback on 429                   │
└─────────────────────────────────────────────────────────────┘
                              │ Fallback (429/timeout/error)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  L2: DeepSeek V4 (Backup - Pay-per-token)                  │
│  • DeepSeek-V4-Pro: Complex (≥30 messages / high-value)    │
│    - Two-stage reasoning (evidence → persona)               │
│    - Cost: ~¥7/analysis                                     │
│  • DeepSeek-V4-Flash: Simple (10-20 messages)              │
│    - Single-pass analysis                                   │
│    - Cost: ~¥3/analysis                                     │
└─────────────────────────────────────────────────────────────┘
                              │ Fallback (API error)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  L3: Rule-Based Engine (Final Fallback)                    │
│  • Pure Python logic, 100% availability                     │
│  • Zero cost                                                │
└─────────────────────────────────────────────────────────────┘
```

**Cost Optimization Strategy (84% savings):**

1. **Intelligent Model Routing** (model_selection.py):
   - Complexity scoring based on chat count, customer value, order diversity
   - VIC/V3/V2 customers → DeepSeek Pro (highest quality)
   - 10-20 chats → DeepSeek Flash (balanced)
   - <10 chats or no chats → MiniMax (low cost)

2. **Incremental Analysis** (analyzer_orchestrator.py):
   - First-time: 50 recent chats
   - Refresh: 20 new + 5 historical context (dynamic window)
   - Cache invalidation: snapshot-based (analyzed_last_purchase_date / analyzed_last_chat_date)
   - No TTL - only re-analyze when data changes

3. **Context Optimization**:
   - Profile fields: 25 → 11 (-56% reduction)
   - Chat-first JSON ordering (prevents truncation)
   - Max context: 15K chars (full) / 8K chars (incremental)

4. **Performance Benchmarks**:
   - MiniMax M3: 43s (after Round 5 optimization, was 78s)
   - DeepSeek V4 Flash: 3-5s
   - DeepSeek V4 Pro: 7-10s (two-stage reasoning)

### Database Architecture

**Core Tables:**

1. **target_buyers_precomputed** - Main 360° customer view
   - Historical metrics: GMV, refunds, net sales, orders, refund rate
   - Time windows: Rolling 24M (VIP calculation), L6M, L1Y
   - Chat metrics: frequency, last contact date, total messages
   - Smart tags: VIP level, discount sensitivity, churn risk, category preferences
   - RFM segmentation: recency/frequency/monetary scores + 13 segments
   - AI analysis: sentiment_label, dominant_intent (from cache table)
   - Auto-updates: Daily at 11:00 AM via MySQL event

2. **target_buyers_precomputed_history** - Daily snapshots (partitioned by month)
   - Enables YoY comparison and trend analysis
   - Partition maintenance: auto-cleanup old partitions
   - Stored procedure: `refresh_target_buyers_asof(date)`

3. **buyer_ai_analysis_cache** - AI analysis results
   - Persona: summary, key_interests, pain_points, recommended_action
   - Sentiment: score, label, dominant_intent
   - Separate timestamps for persona vs sentiment (independent refresh)
   - Snapshot fields: analyzed_last_purchase_date, analyzed_last_chat_date

4. **keyword_analysis_cache** - Pre-aggregated keyword counts (9 categories)
   - Buyer-type filtering (SMOKER/VIC/BOTH/NON_TARGET)
   - Category distribution cache
   - Message count metadata

5. **customer_service_log** - CRM operations tracking
   - Status: pending/contacted/resolved
   - Follow-up timestamps and notes

6. **ai_api_cost_log** - Cost monitoring
   - Tracks API calls per model (MiniMax/DeepSeek-Pro/DeepSeek-Flash)
   - Token usage and estimated costs

**SQL File Organization:**

SQL queries are stored as separate files (not embedded in Python code):

- `backend/database/sql/target_buyers/*.sql` - Optimized queries for v2 API
- `backend/database/sql/create_target_buyers_precomputed.sql` - Table + procedures + events
- `backend/database/sql/*.sql` - Schema migrations and fixes

**Pattern**: SQL files use `[[CONDITION]]` syntax for optional WHERE clauses, dynamically removed by `TargetBuyerQueries` class.

**Performance:**

| Operation | Time | Optimization |
|-----------|------|--------------|
| All buyers list | < 0.5s | Indexed buyer_nick + vip_level + churn_risk |
| Single buyer profile | < 0.1s | Primary key lookup |
| Dashboard metrics | < 0.1s | Aggregation on indexed columns |
| YoY comparison | < 0.2s | Partitioned history table |

### Frontend Architecture

**App Structure:**

- `src/App.tsx` - Main app shell with routing
- `src/views/DashboardOverview.tsx` - Main dashboard (metrics + charts + priority list)
- `src/views/ChatAnalysis.tsx` - Customer 360° detail page
- `src/views/SettingsView.tsx` - Configuration panel
- `src/views/ExternalInfoConfig.tsx` - Offline data management

**Dashboard Components** (src/components/dashboard/):

- `MetricCards.tsx` - 4-group operational metrics (customer health, follow-up priority, sales opportunities, service quality)
- `KeywordAnalysisPanel.tsx` - SMOKER keyword cloud (9 categories: 赠品/包装/维修保养/退换货/产品推荐咨询/产品参数咨询/价格/物流/投诉反馈)
- `PriorityAttentionBoard.tsx` - CRM actionable customer list with tabs:
  - Priority customers (high-value opportunities)
  - Churn warning (3-condition severity tiers, configurable 60D/90D/180D windows)
- `SentimentCharts.tsx` - Sentiment distribution visualization
- `YoYCompareChart.tsx` - Year-over-year comparison
- `HistoryTrendsSection.tsx` - Time-series trends

**Common Components** (src/components/common/):

- `NotionCard.tsx`, `NotionTag.tsx` - Notion-style UI primitives
- `SearchBar.tsx`, `StatusButtonGroup.tsx` - Reusable controls
- `ConfirmDialog.tsx`, `ErrorAlert.tsx`, `LoadingState.tsx` - Interaction patterns

**State Management**: Local component state with React hooks (useState, useMemo)

**Styling**: Tailwind CSS with Notion-inspired design tokens (low-saturation pastels)

## Target Buyers Optimization (Key Feature)

### What It Does

The v2 API focuses on **high-value customers only**, dramatically improving performance:

- **Smoker Buyers**: Purchased Pipes or Lighters categories
- **VIC Buyers**: Rolling 24-month net sales >= 30,000
- **BOTH**: Customers who are both Smoker and VIC (core high-value segment)

### VIP Level Calculation

Based on **Rolling 24-Month Net Sales**:

- V3: >= 450,000
- V2: 150,000 - 449,999
- V1: 50,000 - 149,999
- V0: 30,000 - 49,999
- Non-VIP: < 30,000

### Performance Gains

| Operation | Before (v1 VIEW) | After (v2 Precomputed) | Improvement |
|-----------|------------------|------------------------|-------------|
| Buyer list | 10-30s | < 0.5s | **20-60x** |
| Dashboard metrics | 5-15s | < 0.1s | **50-150x** |
| Buyer details | 2-5s | < 0.1s | **20-50x** |
| AI analysis (cached) | 60-90s | < 0.5s | **120-180x** |

## Database Configuration

- Database credentials are loaded from `~/database_config.json` via `DBConfigManager`
- Shared configuration with `chat-history-crawler` project
- Set `DB_NAME_TO_USE` environment variable to specify which database to use
- Default database: `aliyunDB`

## Key Data Models

### Customer Tags & Labels

- **VIP Level**: V3/V2/V1/V0/Non-VIP (based on Rolling 24M net sales)
- **Customer Type**: New/Old (from `client_monthly_tag` field)
- **Buyer Type**: SMOKER/VIC/BOTH/NON_TARGET
- **Discount Sensitivity**: High/Medium/Low (based on discount order ratio)
- **Churn Risk**: High/Medium/Low (based on purchase and chat recency)
- **Follow Priority**: Urgent/High/Medium/Low (AI-driven)
- **Category Preference**: Top 3 product categories by order count
- **RFM Segment**: 13 segments (Champions, Loyal Customers, Potential Loyalists, etc.)

See `docs/架构设计/数据模型设计.md` for complete tag system design.

### AI Persona Analysis

Output fields:

- **summary**: 2-3 sentence customer persona
- **key_interests**: Array of interest points (e.g., "高端烟斗收藏", "奢侈品消费偏好")
- **pain_points**: Array of pain points (e.g., "尺码选择困难", "物流时效期望高")
- **recommended_action**: Specific sales recommendation (e.g., "推荐限量版烟斗新品")
- **method**: Analysis method used (MiniMax-M3 / DeepSeek-V4-Pro / DeepSeek-V4-Flash / Rule-based)

### Sentiment & Intent Analysis

Output includes:

- **sentiment_label**: Positive/Neutral/Negative
- **sentiment_score**: 0.0-1.0 (confidence)
- **dominant_intent**: Pre-sale Inquiry / Post-sale Support / Logistics / Usage Guide / Complaint
- **intent_distribution**: JSON object with intent percentages

### Keyword Analysis (9 Categories)

For SMOKER customers (Pipes/Lighters buyers):

1. **赠品** (Gifts) - Gift requests, complimentary items
2. **包装** (Packaging) - Packaging quality, gift wrapping
3. **维修保养** (Maintenance) - Repair, cleaning, care instructions
4. **退换货** (Returns/Exchanges) - Return/exchange requests
5. **产品推荐咨询** (Product Recommendations) - Product suggestions, alternatives
6. **产品参数咨询** (Product Specs) - Size, material, specifications
7. **价格** (Price) - Pricing, discounts, promotions
8. **物流** (Logistics) - Shipping, delivery, tracking
9. **投诉反馈** (Complaints) - Quality issues, service complaints

## Important Conventions

### SQL Query Files

When adding new queries:

1. Create `.sql` file in `backend/database/sql/target_buyers/`
2. Use `[[OPTIONAL_CONDITION]]` syntax for dynamic WHERE clauses
3. Load via `TargetBuyerQueries` class in Python
4. Never embed complex SQL in Python code

### API Versioning

- **Production**: Use `/api/v2/*` routes (precomputed table)
- **Deprecated**: `/api/v1/*` routes (slow, legacy VIEW queries)
- **Frontend**: Always use v2 APIs

### Database Updates

- **Schema changes**: Create SQL script in `backend/database/sql/`
- **Data updates**: Use stored procedures or Python scripts in `scripts/`
- **Testing**: Always test on non-production database first

### Code Organization

- **Backend**: Feature-based modules (`analytics/`, `database/`, `api/`, `ai/`)
- **Frontend**: View-based organization (`views/`, `components/dashboard/`, `components/common/`)
- **SQL**: Separated by feature (`target_buyers/` for optimized queries)

## Development Workflow

1. **New Feature Development**:
   - Create SQL query file in `backend/database/sql/target_buyers/`
   - Add query method to `TargetBuyerQueries` class
   - Add business logic to `TargetBuyerAnalyzer` class
   - Add API endpoint to `backend/api/target_routes.py` (v2 prefix)
   - Create/update frontend components in `src/components/`
   - Update frontend to call new v2 endpoint

2. **AI Analysis Enhancement**:
   - Update prompts in `backend/ai/prompts/`
   - Adjust model selection logic in `backend/ai/model_selection.py`
   - Test fallback chain (MiniMax → DeepSeek → Rule-based)
   - Monitor cost via `ai_api_cost_log` table

3. **Performance Optimization**:
   - Always use precomputed table for new features
   - Monitor query execution times with `EXPLAIN`
   - Add indexes to `target_buyers_precomputed` table if needed
   - Consider partitioning for large history tables

4. **Database Schema Changes**:
   - Write migration SQL script
   - Update `create_target_buyers_precomputed.sql` if changing precomputed table
   - Test stored procedure `refresh_target_buyers_asof(date)`
   - Verify auto-update event is working (daily at 11:00 AM)

## Recent Features (June 2026)

### Round 4-5: Incremental AI Analysis Optimization

- **Incremental mode**: First-time 50 chats / Refresh 20+5=25 chats
- **Dynamic context window**: More new messages → less historical context
- **Performance**: 45% faster for MiniMax (78s → 43s)
- **Prompt optimization**: 25 → 11 profile fields, chat-first JSON ordering

### Round 2-3: Churn Warning Enhancement

- **3-condition logic**: Segment degradation + churn risk升级 + purchase power collapse
- **Configurable windows**: 60D/90D/180D (default 90D)
- **Severity tiers**: 1-4 with selection reasons display
- **Thresholds**: 60D=¥10K, 90D=¥15K, 180D=¥20K

### March 2026: Keyword Analysis Module

- **9-category taxonomy** for SMOKER customers
- **Pre-computed cache** for fast aggregation
- **Multi-buyer-type filtering** (SMOKER/VIC/BOTH/NON_TARGET)
- **De-duplication rules** (remove包含关系)

### February 2026: Priority Attention Board

- **Exportable customer list** with CSV export
- **Two tabs**: Priority customers + Churn warning
- **AI-driven follow-up priority**: Urgent/High/Medium/Low

## Security Considerations

- All SQL queries use parameterized statements (SQL injection protection)
- Error handling with specific exception types
- Environment variables for sensitive data (API keys, database credentials)
- Type safety: TypeScript on frontend, type hints on backend
- No secrets in code, logs, or version control

## Documentation

- **Complete docs**: `docs/README.md`
- **AI analysis optimization**: `docs/plans/2026-02-24-ai-optimization-summary.md`
- **Target buyers feature**: `docs/用户文档/目标买家功能总结.md`
- **Deployment guide**: `docs/部署运维/目标买家部署指南.md`
- **Data model**: `docs/架构设计/数据模型设计.md`
- **Field reference**: `docs/field_reference/客户月度标签字段.md`

## Frontend Development Guidelines

### UI/Visual Modifications Priority

**对于所有前端视觉相关的修改，优先调用 `frontend-design` skill**：

当任务涉及以下内容时，应首先使用 frontend-design skill：

- UI组件布局调整
- 样式和颜色修改
- 新增视觉模块（卡片、图表、标签等）
- 交互组件设计（按钮、筛选器、表单等）
- Notion风格UI优化

使用方式：在开始前端视觉修改前，调用 `Skill` tool 并指定 `skill: "frontend-design"`，让skill指导设计实现。

## Project Memory Management

项目使用持久化 memory 文件来记录开发历史、技术决策和重要信息。

### Memory 文件位置

Memory 文件存储在项目目录下（参与版本控制）：
```
docs/memory/
├── MEMORY.md          # 主记忆文件（开发历史、已完成功能、技术细节）
└── *.md               # 专题记忆文件（按需创建）
```

**重要**：每次会话开始时，应主动读取 `docs/memory/MEMORY.md` 了解项目状态和历史决策。

### 何时更新 Memory

**必须更新的场景：**
1. **完成重要功能**：记录功能概述、文件结构、技术细节
2. **做出技术决策**：记录决策内容和理由
3. **发现并解决重要问题**：记录问题和解决方案
4. **用户明确要求记忆**：用户说"记住这个"、"以后都这样"等

**不应记录的内容：**
- 临时状态、未完成的任务细节
- 一次性调试信息
- 重复或矛盾的信息

### Memory 更新规则

1. **MEMORY.md**：保持在 200 行以内，超过 200 行时：
   - 将详细内容拆分到专题文件（如 `keyword-analysis.md`）
   - 在 MEMORY.md 中保留摘要和链接

2. **专题文件命名**：使用小写字母和连字符，如 `keyword-analysis.md`

3. **更新流程**：
   ```
   1. 使用 Read 工具读取现有 memory 文件
   2. 使用 Edit 工具更新内容（不要完全覆盖）
   3. 移除过时或错误的信息
   4. 确保信息简洁、准确、有价值
   ```

4. **用户修正时**：如果用户指出 memory 中的错误，必须立即修正，不要等待多次确认

### Memory 与 Git

Memory 文件位于 `docs/memory/`，应参与版本控制：
- 完成重要功能后，提交 memory 更新
- 提交信息示例：`docs: update memory for keyword analysis optimization`
