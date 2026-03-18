# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SmokeSignal Analytics is a Notion-style CRM dashboard for e-commerce customer service analytics. It visualizes customer sentiment, chat history, purchase behavior, and AI-powered customer insights for e-commerce operations (specifically Taobao/Tmall).

**Tech Stack:**

- **Frontend**: React 19.2.3 + TypeScript + Vite 6.2.0 + Recharts 3.6.0
- **Backend**: FastAPI (Python) + MySQL/PostgreSQL
- **AI**: Multi-model pipeline (DeepSeek-V3.2 primary + Zhipu GLM-4.7 fallback + Rule-based fallback) for persona and sentiment/intent analysis
- **Data Source**: Playwright-based crawler from Qianniu Workbench (Taobao/Tmall)

## Common Development Commands

### Frontend Development

```bash
# Install dependencies
npm install

# Start dev server (runs on http://localhost:3000)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Backend Development

```bash
# Start backend server (runs on http://localhost:8000)
./scripts/start-backend.sh  # Linux/Mac
scripts\start-backend.bat   # Windows

# Or directly with Python
python -m backend.main

# Run backend with uvicorn (from backend directory)
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
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
# Deploy target buyers precomputed table (creates table, stored procedure, and daily update event)
./scripts/deploy_mysql.sh  # Linux/Mac
# Note: Update database credentials in the script first

# Manual refresh of precomputed data
mysql -u username -p database_name -e "CALL refresh_target_buyers_precomputed();"
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
FastAPI Backend (Buyer Analysis + Target Buyer Optimization)
    ↓
React Frontend (Dashboard)
```

### Backend Architecture

**Two-Tier API System:**

1. **v1 API (`/api/v1/*`)** - Real-time queries from VIEW
   - Direct queries to `dunhill_t01_trade_line` VIEW
   - Slow performance (10-30 seconds per query)
   - Used for: Legacy functionality, real-time data needs
2. **v2 API (`/api/v2/*`)** - Precomputed table (OPTIMIZED) ⭐
   - Uses `target_buyers_precomputed` table
   - **10-50x faster** performance (< 0.5 seconds)
   - Auto-updates daily at 11:00 AM via MySQL event
   - Filters for high-value customers: Smoker (Pipes/Lighters) + VIC (Rolling 24M >= 30K)
   - **Preferred for all new development**

**Key Backend Components:**

- `backend/analytics/target_buyer_analyzer.py` - Optimized analyzer using precomputed table
- `backend/analytics/buyer_analyzer.py` - Legacy analyzer (slow)
- `backend/database/target_buyer_queries.py` - SQL query loader (loads from .sql files)
- `backend/database/queries.py` - Legacy query builder
- `backend/api/target_routes.py` - v2 API routes (prefix: `/api/v2`)
- `backend/ai/analyzer_orchestrator.py` - Persona orchestration with multi-level fallback and cache
- `backend/ai/deepseek_client.py` - Primary AI client for persona and sentiment/intent
- `backend/ai/zhipu_client.py` - Fallback AI client (GLM-4.7)
- `backend/ai/batch_analyzer.py` - Batch sentiment/intent analysis pipeline

### SQL File Organization

**SQL queries are stored as separate files** (not embedded in Python code):

- `backend/database/sql/target_buyers/*.sql` - 10 optimized query files for v2 API
- `backend/database/sql/create_target_buyers_precomputed.sql` - Table creation + stored procedure + auto-update event
- `backend/database/sql/*.sql` - Various database scripts and fixes

**Pattern**: SQL files use `[[CONDITION]]` syntax for optional WHERE clauses, dynamically removed by `TargetBuyerQueries` class.

### Frontend Architecture

**Single-Page Application Structure:**

- `src/App.tsx` - Main app with 3 views: Dashboard Overview, Chat & CRM, Configuration
- `src/components/common/NotionCard.tsx` - Reusable card component
- `src/components/common/NotionTag.tsx` - Tag component with color variants
- Uses Recharts for all visualizations (Line, Bar, Pie, Radar charts)

**State Management**: Local component state with React hooks (useState, useMemo)

**Styling**: Tailwind CSS with Notion-inspired design tokens (defined inline in App.tsx)

## Target Buyers Optimization (Key Feature)

### What It Does

The v2 API focuses on **high-value customers only**, dramatically improving performance:

- **Smoker Buyers**: Purchased Pipes or Lighters categories
- **VIC Buyers**: Rolling 24-month net sales >= 30,000
- **BOTH**: Customers who are both Smoker and VIC (core high-value segment)

### Precomputed Data

The `target_buyers_precomputed` table contains:

- Historical metrics: GMV, refunds, net sales, orders, refund rate
- Time-based metrics: Rolling 24M (VIP calculation), L6M, L1Y
- Chat metrics: Communication frequency, last contact date
- Smart tags: VIP level (V3/V2/V1/V0), discount sensitivity, churn risk, category preferences
- Auto-updates: Daily at 11:00 AM via MySQL event scheduler

### VIP Level Calculation

Based on **Rolling 24-Month Net Sales**:

- V3: >= 450,000
- V2: 150,000 - 449,999
- V1: 50,000 - 149,999
- V0: 30,000 - 49,999
- Non-VIP: < 30,000

### Performance Gains

| Operation         | v1 (VIEW) | v2 (Precomputed) | Improvement |
| ----------------- | --------- | ---------------- | ----------- |
| Buyer list        | 10-30s    | < 0.5s           | **20-60x**  |
| Dashboard metrics | 5-15s     | < 0.1s           | **50-150x** |
| Buyer details     | 2-5s      | < 0.1s           | **20-50x**  |

## Database Configuration

- Database credentials are loaded from `~/database_config.json` via `DBConfigManager`
- Shared configuration with `chat-history-crawler` project
- Set `DB_NAME_TO_USE` environment variable to specify which database to use
- Default database: `aliyunDB`

## Key Data Models

### Customer Tags & Labels

- **VIP Level**: V3/V2/V1/V0/Non-VIP (based on Rolling 24M net sales)
- **Customer Type**: New/Old (from `client_monthly_tag` field)
- **Discount Sensitivity**: High/Medium/Low (based on discount order ratio)
- **Churn Risk**: High/Medium/Low (based on purchase and chat recency)
- **Category Preference**: Top 3 product categories by order count

See `docs/架构设计/数据模型设计.md` for complete tag system design.

### AI Persona Analysis

Persona analysis uses a multi-level strategy:

- **Primary**: DeepSeek (Reasoner/Chat by scenario)
- **Fallback**: Zhipu GLM-4.7
- **Final fallback**: Rule-based analyzer

Output fields:

- **summary**: 2-3 sentence customer persona
- **key\_interests**: Array of interest points
- **pain\_points**: Array of pain points
- **recommended\_action**: Specific sales recommendation

### Sentiment & Intent Analysis

Sentiment/intent uses a batch pipeline:

- **Primary**: Zhipu GLM-4.7
- **Fallback**: DeepSeek sentiment-intent analysis
- **Final fallback**: Rule-based analysis

Output includes:

- **sentiment\_label / sentiment\_score**
- **intent\_distribution / dominant\_intent**

## Important Conventions

### SQL Query Files

When adding new queries:

1. Create `.sql` file in `backend/database/sql/target_buyers/`
2. Use `[[OPTIONAL_CONDITION]]` syntax for dynamic WHERE clauses
3. Load via `TargetBuyerQueries` class in Python
4. Never embed complex SQL in Python code

### API Versioning

- **New features**: Use `/api/v2/*` routes (precomputed table)
- **Legacy**: `/api/v1/*` routes (slow, will be deprecated)
- **Frontend**: Default to v2 APIs, only use v1 if v2 doesn't support the feature

### Database Updates

- **Schema changes**: Create SQL script in `backend/database/sql/`
- **Data updates**: Use stored procedures or Python scripts in `scripts/`
- **Testing**: Always test on non-production database first

### Code Organization

- **Backend**: Feature-based modules (`analytics/`, `database/`, `api/`, `ai/`)
- **Frontend**: Currently single-file (App.tsx), plan to refactor
- **SQL**: Separated by feature (`target_buyers/` for optimized queries)

## Development Workflow

1. **New Feature Development**:
   - Create SQL query file in `backend/database/sql/target_buyers/`
   - Add query method to `TargetBuyerQueries` class
   - Add business logic method to `TargetBuyerAnalyzer` class
   - Add API endpoint to `backend/api/target_routes.py` (v2 prefix)
   - Update frontend to call new v2 endpoint
2. **Performance Optimization**:
   - Always use precomputed table approach for new features
   - Monitor query execution times with `EXPLAIN`
   - Add indexes to `target_buyers_precomputed` table if needed
3. **Database Schema Changes**:
   - Write migration SQL script
   - Update `create_target_buyers_precomputed.sql` if changing precomputed table
   - Test stored procedure `refresh_target_buyers_precomputed()`
   - Verify auto-update event is working

## Security Considerations

- All SQL queries use parameterized statements (SQL injection protection)
- Error handling with specific exception types
- Environment variables for sensitive data (API keys, database credentials)
- Type safety: TypeScript on frontend, type hints on backend

## Documentation

- **Complete docs**: `docs/README.md`
- **Target buyers feature**: `docs/用户文档/目标买家功能总结.md`
- **Deployment guide**: `docs/部署运维/目标买家部署指南.md`
- **Data model**: `docs/架构设计/数据模型设计.md`
- **Field reference**: `docs/field_reference/客户月度标签字段.md`

## Frontend Development Guidelines

### UI/Visual Modifications Priority

**对于所有前端视觉相关的修改，优先调用** **`frontend-design`** **skill**：

当任务涉及以下内容时，应首先使用frontend-design skill：

- UI组件布局调整
- 样式和颜色修改
- 新增视觉模块（卡片、图表、标签等）
- 交互组件设计（按钮、筛选器、表单等）
- Notion风格UI优化

使用方式：在开始前端视觉修改前，调用 `Skill` tool 并指定 `skill: "frontend-design"`，让skill指导设计实现。
