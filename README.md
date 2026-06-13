<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# SmokeSignal E-Commerce Analytics

A Notion-style CRM dashboard for luxury e-commerce customer service analytics. Built for dunhill China's Taobao/Tmall operations, featuring AI-powered customer insights, sentiment analysis, and intelligent cost optimization.

**View your app in AI Studio:** https://ai.studio/apps/drive/14aS21FRXtWxJc9UKqX5inwFDswfXQW6t

## Features

- **360° Customer Profiles** - Comprehensive buyer analytics with LTV, RFM segmentation, VIP tiering, and purchase patterns
- **AI-Powered Insights** - Multi-model persona analysis with 84% cost savings (MiniMax M3 → DeepSeek V4 → Rule-based)
- **Priority Attention Board** - CRM actionable customer list with churn warning (3-condition severity tiers)
- **Keyword Analysis** - 9-category issue taxonomy for SMOKER customers (Pipes/Lighters buyers)
- **Performance Optimization** - 20-60x faster queries via precomputed tables and daily snapshots
- **Interactive Dashboards** - Real-time metrics, YoY comparison, time-series trends
- **Incremental AI Analysis** - Smart caching with snapshot-based invalidation (no TTL)
- **Notion-Style UI** - Clean, professional interface with low-saturation pastel color scheme

## Tech Stack

### Frontend
- **React 19** with TypeScript
- **Vite 6** for fast development and HMR
- **Recharts 3.6** for data visualization (line, bar, pie, radar charts)
- **Tailwind CSS** for Notion-inspired styling
- **Lucide React** for icons

### Backend
- **FastAPI** for async REST API
- **MySQL 8.0+** with partitioning and stored procedures
- **AI Models**:
  - **MiniMax M3** (L1 - primary, monthly subscription)
  - **DeepSeek V4 Pro/Flash** (L2 - backup, pay-per-token)
  - **Rule-based Engine** (L3 - final fallback)
- **Playwright** integration for Qianniu Workbench data crawling

## Documentation

**Documentation Center**: [`docs/README.md`](./docs/README.md)

### Core Documentation
| Document | Description |
|----------|-------------|
| [AI Optimization Summary](./docs/plans/2026-02-24-ai-optimization-summary.md) | 84% cost reduction strategy (incremental analysis + intelligent routing) |
| [Target Buyers Feature](./docs/用户文档/目标买家功能总结.md) | 20-60x performance improvement via precomputed tables |
| [Data Model Design](./docs/架构设计/数据模型设计.md) | Buyer tag system, RFM segmentation, VIP tiering |
| [Deployment Guide](./docs/部署运维/目标买家部署指南.md) | MySQL table creation, stored procedures, partitioning |
| [Field Reference](./docs/field_reference/客户月度标签字段.md) | Complete field definitions for customer profiles |

---

## Quick Start

### Prerequisites
- Node.js 18+ (for frontend)
- Python 3.9+ (for backend)
- MySQL 8.0+ database (with partitioning support)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/NovelAn/smokesignal-ecommerce-analytics.git
   cd smokesignal-ecommerce-analytics
   ```

2. **Install frontend dependencies**
   ```bash
   npm install
   ```

3. **Configure environment**
   ```bash
   # Create .env file with your API keys
   cat > .env << EOF
   # Database
   DB_CONFIG_FILE=~/database_config.json
   DB_NAME_TO_USE=aliyunDB

   # MiniMax AI (Primary - L1)
   MINIMAX_API_KEY=sk-xxxxxxxx
   MINIMAX_BASE_URL=https://api.minimax.chat/v1
   MINIMAX_MODEL=MiniMax-M3

   # DeepSeek AI (Backup - L2)
   DEEPSEEK_API_KEY=sk-xxxxxxxx
   DEEPSEEK_MODEL_PRO=deepseek-v4-pro
   DEEPSEEK_MODEL_FLASH=deepseek-v4-flash

   # AI Cache (snapshot-based, no TTL)
   AI_ENABLE_CACHE=true
   EOF
   ```

4. **Run development servers**

   Frontend (runs on http://localhost:3000):
   ```bash
   npm run dev
   ```

   Backend (runs on http://localhost:8000):
   ```bash
   ./scripts/start-backend.sh  # Linux/Mac
   scripts\start-backend.bat   # Windows
   ```

## Project Structure

```
├── backend/          # Python FastAPI backend
│   ├── ai/           # AI analysis modules
│   │   ├── analyzer_orchestrator.py  # Multi-model orchestration (L1→L2→L3)
│   │   ├── model_selection.py        # Intelligent routing (complexity scoring)
│   │   ├── minimax_client.py         # MiniMax M3 client (primary)
│   │   ├── deepseek_client.py        # DeepSeek V4 Pro/Flash client (backup)
│   │   └── rule_based_analyzer.py    # Rule-based fallback
│   ├── analytics/    # Data analytics
│   │   ├── target_buyer_analyzer.py  # Customer analytics engine
│   │   └── keyword_categories.py     # 9-category keyword taxonomy
│   ├── api/          # API routes
│   │   ├── target_routes.py          # Main API (v2) - 2,683 lines
│   │   └── external_routes.py        # External records API
│   └── database/     # Database layer
│       ├── target_buyer_queries.py   # SQL query loader
│       └── sql/                      # SQL files (not embedded in code)
├── src/              # React frontend source
│   ├── views/        # Main views
│   │   ├── DashboardOverview.tsx     # Main dashboard
│   │   ├── ChatAnalysis.tsx          # Customer 360° detail page
│   │   ├── SettingsView.tsx          # Configuration panel
│   │   └── ExternalInfoConfig.tsx    # Offline data management
│   └── components/   # Reusable components
│       ├── dashboard/                # Dashboard-specific components
│       │   ├── MetricCards.tsx       # 4-group operational metrics
│       │   ├── KeywordAnalysisPanel.tsx # 9-category keyword cloud
│       │   ├── PriorityAttentionBoard.tsx # CRM actionable list
│       │   └── YoYCompareChart.tsx   # Year-over-year comparison
│       └── common/                   # Shared UI primitives
├── docs/             # Documentation
├── scripts/          # Utility scripts
└── tests/            # Test files
```

## Key Features

### 1. Multi-Model AI Analysis with Cost Optimization

**3-Tier Intelligent Routing (84% Cost Savings):**

```
┌─────────────────────────────────────────────────────────────┐
│  L1: MiniMax M3 (Primary - Monthly Subscription)           │
│  • All persona analysis starts here                         │
│  • ¥0 per call (unlimited within plan)                      │
│  • Fast fallback on 429 errors (max_retries=0)              │
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
│  • Pure Python logic, 100% availability, ¥0 cost            │
└─────────────────────────────────────────────────────────────┘
```

**Intelligent Model Selection:**
- Complexity scoring based on chat count, customer value, order diversity
- VIC/V3/V2 customers → DeepSeek Pro (highest quality)
- 10-20 chats → DeepSeek Flash (balanced cost/quality)
- <10 chats or no chats → MiniMax (low cost)

**Incremental Analysis Optimization:**
- First-time: 50 recent chats
- Refresh: 20 new + 5 historical context (dynamic window)
- Snapshot-based cache invalidation (no TTL)
- 45% faster: MiniMax 78s → 43s (Round 5 optimization)

### 2. Performance Optimization via Precomputed Tables

| Operation | Before (v1 VIEW) | After (v2 Precomputed) | Improvement |
|-----------|------------------|------------------------|-------------|
| Buyer list | 10-30s | < 0.5s | **20-60x** |
| Dashboard metrics | 5-15s | < 0.1s | **50-150x** |
| Buyer details | 2-5s | < 0.1s | **20-50x** |
| AI analysis (cached) | 60-90s | < 0.5s | **120-180x** |

**Optimization Strategies:**
- Daily precomputed table refresh (11:00 AM via MySQL event)
- Partitioned history table (monthly partitions, auto-cleanup)
- Indexed columns: buyer_nick, vip_level, churn_risk, rfm_segment
- Stored procedures for complex aggregations

### 3. Priority Attention Board (CRM Feature)

**Two Tabs:**

1. **Priority Customers** (High-value opportunities):
   - AI-driven follow-up priority (Urgent/High/Medium/Low)
   - VIC customers with recent activity
   - High-intent pre-sale inquiries

2. **Churn Warning** (3-condition severity tiers):
   - Segment degradation detection
   - Churn risk升级 monitoring
   - Purchase power collapse alerts
   - Configurable windows: 60D/90D/180D (default 90D)
   - Severity tiers 1-4 with selection reasons

### 4. Keyword Analysis (9 Categories)

For SMOKER customers (Pipes/Lighters buyers):

| Category | Description | Use Case |
|----------|-------------|----------|
| 赠品 (Gifts) | Gift requests, complimentary items | Loyalty program optimization |
| 包装 (Packaging) | Packaging quality, gift wrapping | Unboxing experience improvement |
| 维修保养 (Maintenance) | Repair, cleaning, care instructions | After-sales service enhancement |
| 退换货 (Returns/Exchanges) | Return/exchange requests | Quality control feedback |
| 产品推荐咨询 (Recommendations) | Product suggestions | Cross-sell opportunities |
| 产品参数咨询 (Specs) | Size, material, specifications | Product description optimization |
| 价格 (Price) | Pricing, discounts, promotions | Pricing strategy insights |
| 物流 (Logistics) | Shipping, delivery, tracking | Logistics partner evaluation |
| 投诉反馈 (Complaints) | Quality issues, service complaints | Operations improvement |

**Features:**
- Pre-computed cache for fast aggregation
- Multi-buyer-type filtering (SMOKER/VIC/BOTH/NON_TARGET)
- De-duplication rules (remove包含关系)
- Visualization: Donut chart + horizontal bar chart

### 5. Customer 360° Profile

**Financial Metrics:**
- Rolling 24M net sales (VIP calculation basis)
- L6M / L1Y performance windows
- Historical GMV, refunds, orders
- Discount sensitivity scoring

**RFM Segmentation:**
- 13 segments: Champions, Loyal Customers, Potential Loyalists, At Risk, etc.
- Recency/Frequency/Monetary scores (1-5 scale)

**Smart Tags:**
- VIP Level: V3/V2/V1/V0/Non-VIP
- Churn Risk: High/Medium/Low
- Follow Priority: Urgent/High/Medium/Low (AI-driven)
- Category Preferences: Top 3 product categories

**AI Analysis:**
- Persona summary (2-3 sentences)
- Key interests and pain points
- Recommended sales actions
- Sentiment label and score
- Dominant intent classification

## Dashboard Components

### Dashboard Overview
- **4-Group Metric Cards**:
  1. Customer Health (sentiment distribution)
  2. Follow-up Priority (urgent/high/medium counts)
  3. Sales Opportunities (VIC/SMOKER/repurchase potential)
  4. Service Quality (negative sentiment, churn risk)
- **Keyword Analysis Panel** - 9-category issue cloud for SMOKER customers
- **Priority Attention Board** - CRM actionable list (priority + churn warning)
- **YoY Comparison** - Year-over-year trends with summary cards
- **History Trends** - Pool summary, VIP distribution, segment trends

### Customer 360° Profile (Chat Analysis View)
- **AI Persona Analysis** - Summary, interests, pain points, recommended actions
- **Financial Dashboard** - LTV, AOV, Rolling 24M, L6M, L1Y metrics
- **Purchase History** - Complete order timeline with status
- **Communication Timeline** - Chat messages grouped by date
- **RFM Segment Card** - Current segment and score breakdown

### Configuration
- **Pipeline Status** - ETL crawler monitoring
- **Dictionary Management** - Keyword tagging configuration
- **Database Connection** - Status and performance metrics
- **External Records** - Offline consumption and private domain communication

## Development

### Frontend Development
```bash
npm run dev          # Start dev server
npm run build        # Build for production
npm run preview      # Preview production build
```

### Backend Scripts
```bash
# Data validation
python scripts/check_data.py
python scripts/debug_data.py

# Database optimization
python scripts/run_sql_optimization.py

# Testing
python tests/run_all_tests.py
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

## Database Schema

**Core Tables:**

1. **target_buyers_precomputed** - Main 360° customer view
   - Auto-updates: Daily at 11:00 AM via MySQL event
   - Indexes: buyer_nick (PK), vip_level, churn_risk, rfm_segment

2. **target_buyers_precomputed_history** - Daily snapshots (partitioned by month)
   - Enables YoY comparison and trend analysis
   - Auto-cleanup: Partitions older than 24 months

3. **buyer_ai_analysis_cache** - AI analysis results
   - Separate timestamps for persona vs sentiment
   - Snapshot-based invalidation (analyzed_last_purchase_date, analyzed_last_chat_date)

4. **keyword_analysis_cache** - Pre-aggregated keyword counts (9 categories)

5. **customer_service_log** - CRM operations tracking (pending/contacted/resolved)

6. **ai_api_cost_log** - Cost monitoring per model

## Security

This project implements security best practices:

- **SQL Injection Protection** - All queries use parameterized statements
- **Error Handling** - Specific exception types with proper logging
- **Type Safety** - Full TypeScript coverage on frontend, type hints on backend
- **Environment Variables** - Sensitive data in .env files (never in code)
- **No Secrets in Version Control** - .gitignore configured for all credential files

## Related Projects

This dashboard integrates with **chat-history-crawler**, a Playwright-based crawler that:
- Crawls chat history from Qianniu Workbench (Taobao/Tmall)
- Intercepts network responses for data extraction
- Stores data in MySQL database

Data Flow:
```
Qianniu Workbench → Playwright Crawler → MySQL → SmokeSignal Dashboard
```

## Recent Updates (June 2026)

### Round 4-5: Incremental AI Analysis Optimization
- Incremental mode: First-time 50 chats / Refresh 20+5=25 chats
- Dynamic context window: More new messages → less historical context
- 45% faster: MiniMax 78s → 43s
- Prompt optimization: 25 → 11 profile fields, chat-first JSON ordering

### Round 2-3: Churn Warning Enhancement
- 3-condition logic: Segment degradation + churn risk升级 + purchase power collapse
- Configurable windows: 60D/90D/180D (default 90D)
- Severity tiers 1-4 with selection reasons display
- Thresholds: 60D=¥10K, 90D=¥15K, 180D=¥20K

### March 2026: Keyword Analysis Module
- 9-category taxonomy for SMOKER customers
- Pre-computed cache for fast aggregation (<0.1s)
- Multi-buyer-type filtering
- Donut chart + horizontal bar chart visualization

### February 2026: Priority Attention Board
- Exportable customer list with CSV export
- Two tabs: Priority customers + Churn warning
- AI-driven follow-up priority (Urgent/High/Medium/Low)

## Contributing

Contributions are welcome! Please:
1. Check existing documentation in `docs/`
2. Follow the project structure conventions
3. Ensure all tests pass
4. Update documentation as needed

## License

[Specify your license here]

## Support

For issues or questions:
- Check documentation in `docs/`
- Review [CLAUDE.md](./CLAUDE.md) for development guidance
- Open an issue on GitHub

---

**Built with AI-powered analytics for luxury e-commerce operations**
