<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# SmokeSignal E-Commerce Analytics

A Notion-style CRM dashboard for e-commerce customer service analytics. Visualizes customer sentiment, chat history, purchase behavior, and AI-powered customer insights.

**View your app in AI Studio:** https://ai.studio/apps/drive/14aS21FRXtWxJc9UKqX5inwFDswfXQW6t

## Features

- **360° Customer Profiles** - Comprehensive buyer analytics with LTV, purchase patterns, and engagement metrics
- **Chat History Analysis** - Complete communication history with sentiment tracking
- **Multi-Model AI Insights** - Customer persona analysis with 3-tier fallback (DeepSeek → Zhipu GLM → Rule-based)
- **Smart Caching** - MySQL-based AI caching with dynamic TTL for 88% cost reduction
- **Interactive Dashboards** - Real-time metrics, keyword analysis, and actionable customer lists
- **Excel Export** - Customer data export functionality
- **Notion-Style UI** - Clean, professional interface with familiar design patterns

## Tech Stack

### Frontend
- **React 19.2.3** with TypeScript
- **Vite 6.2.0** for fast development
- **Recharts 3.6.0** for data visualization
- **Lucide React** for icons
- **Tailwind CSS** for styling

### Backend
- **FastAPI** for REST API
- **PostgreSQL/MySQL** for data storage
- **DeepSeek-V3.2** for deep reasoning AI analysis
- **Zhipu GLM-4.7** for fallback AI analysis
- **Playwright** integration for data crawling

## Documentation

**Documentation Center**: [`docs/README.md`](./docs/README.md)

### Core Documentation
| Document | Description |
|----------|-------------|
| [AI Customer Analysis](./docs/功能文档/AI客户画像分析.md) | Multi-model AI architecture and features |
| [AI Optimization Summary](./docs/plans/2026-02-24-ai-optimization-summary.md) | Cost reduction and caching optimization |
| [Target Buyers Feature](./docs/用户文档/目标买家功能总结.md) | 40-120x performance improvement |
| [Data Model Design](./docs/架构设计/数据模型设计.md) | Buyer tag system and CRM model |
| [Deployment Guide](./docs/部署运维/目标买家部署指南.md) | MySQL table creation and automation |

---

## Quick Start

### Prerequisites
- Node.js 18+ (for frontend)
- Python 3.9+ (for backend)
- PostgreSQL or MySQL database

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

   # DeepSeek AI (Primary)
   DEEPSEEK_API_KEY=sk-xxxxxxxx
   DEEPSEEK_MODEL_R1=deepseek-reasoner
   DEEPSEEK_MODEL_CHAT=deepseek-chat

   # Zhipu AI (Fallback)
   ZHIPU_API_KEY=xxxxxxxx
   ZHIPU_MODEL=glm-4-plus

   # AI Cache
   AI_CACHE_TTL_DAYS=30
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
│   │   ├── analyzer_orchestrator.py  # Multi-model orchestration
│   │   ├── deepseek_client.py        # DeepSeek client
│   │   ├── zhipu_client.py           # Zhipu client
│   │   └── cache_manager.py          # AI caching
│   ├── analytics/    # Data analytics
│   ├── api/          # API routes
│   └── database/     # Database layer
├── src/              # React frontend source
├── docs/             # Documentation
├── scripts/          # Utility scripts
└── tests/            # Test files
```

## Key Features

### Multi-Model AI Analysis System

```
┌─────────────────────────────────────────────────────────────┐
│  L1: DeepSeek-V3.2 (Primary)                                │
│  • Deep inference with chat history                         │
│  • Quick analysis without chat history                      │
└─────────────────────────────────────────────────────────────┘
                              │ Fallback (429/timeout/error)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  L2: Zhipu GLM-4.7 (Fallback)                               │
│  • Monthly subscription - no per-call cost                  │
│  • Reliable backup when DeepSeek unavailable                │
└─────────────────────────────────────────────────────────────┘
                              │ Fallback (API error)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  L3: Rule-Based Engine (Final Fallback)                     │
│  • Zero cost, 100% availability                             │
└─────────────────────────────────────────────────────────────┘
```

### AI Caching with Dynamic TTL

| VIP Level | Cache TTL | Reason |
|-----------|-----------|--------|
| V3/V2 (High Value) | 7 days | Data changes frequently |
| V1/Has Chat | 14 days | Behavior may change |
| Non-VIP/No Chat | 30 days | Stable consumption data |

### Performance Optimization

| Operation | Before | After | Improvement |
|-----------|--------|-------|-------------|
| Buyer list | 10-30s | < 0.5s | **20-60x** |
| Dashboard metrics | 5-15s | < 0.1s | **50-150x** |
| AI analysis (cached) | 60-90s | < 0.5s | **120-180x** |

### Cost Optimization

- **Before**: ¥21,000/month (100% DeepSeek-R1)
- **After**: ~¥2,500/month (mixed strategy + caching)
- **Savings**: **88% cost reduction**

## Dashboard Components

### Dashboard Overview
- **Metrics Overview** - Total conversations, sentiment score, urgent issues
- **Keyword Analysis** - Category distribution and top keywords with time filtering
- **Actionable Customers** - Priority board for churn risk, high-value customers
- **Trend Charts** - Sentiment, intent distribution, peak hours

### Customer 360° Profile
- **AI Persona Analysis** - Summary, key interests, pain points, sales opportunities
- **Financial Metrics** - LTV, AOV, discount sensitivity, Rolling 24M performance
- **Purchase History** - Complete order history with status
- **Communication** - Chat messages grouped by date

### Configuration
- **Pipeline Status** - ETL crawler monitoring
- **Dictionary Management** - Keyword tagging configuration
- **Database Connection** - Connection status and metrics

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

## Security

This project implements several security best practices:

- **SQL Injection Protection** - All queries use parameterized statements
- **Error Handling** - Specific exception types with proper logging
- **Type Safety** - Full TypeScript coverage on frontend
- **Environment Variables** - Sensitive data in .env files

## Related Projects

This dashboard integrates with **chat-history-crawler**, a Playwright-based crawler that:
- Crawls chat history from Qianniu Workbench (Taobao/Tmall)
- Intercepts network responses for data extraction
- Stores data in PostgreSQL database

Data Flow:
```
Qianniu Workbench → Playwright Crawler → MySQL → This Dashboard
```

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

**Built with AI-powered analytics**
