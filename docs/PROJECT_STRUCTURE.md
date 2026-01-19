# SmokeSignal Analytics - Project Structure

## Overview

This document describes the organized directory structure of the SmokeSignal E-Commerce Analytics project.

## Directory Structure

```
smokesignal-ecommerce-analytics/
├── backend/                      # Python FastAPI backend
│   ├── analytics/               # Business logic
│   │   ├── buyer_analyzer.py   # Buyer profile analysis
│   │   ├── tag_calculator.py  # Customer tag calculation
│   │   └── __init__.py
│   ├── api/                     # API routes
│   │   ├── routes.py           # REST API endpoints
│   │   └── __init__.py
│   ├── ai/                      # AI integration
│   │   ├── zhipu_client.py     # Zhipu AI client
│   │   └── __init__.py
│   ├── database/                # Database layer
│   │   ├── connection.py       # DB connection management
│   │   ├── db_config_manager.py
│   │   ├── queries.py          # SQL queries (parameterized)
│   │   ├── cache.py            # Query caching
│   │   ├── sql/                # SQL scripts
│   │   │   ├── create_buyer_summary_table_optimized.sql
│   │   │   ├── dunhill_t01_trade_line.sql
│   │   │   ├── fix_stored_procedure_after_view.sql
│   │   │   ├── fix_stored_procedure_with_refund.sql
│   │   │   └── check_ddl_history.sql
│   │   └── __init__.py
│   ├── utils/                   # Utility functions
│   │   ├── datetime_helpers.py # Datetime parsing helpers
│   │   └── __init__.py
│   ├── config.py                # Configuration settings
│   ├── main.py                  # FastAPI application entry point
│   └── README.md
│
├── src/                         # React frontend source
│   ├── components/              # React components
│   │   ├── common/             # Reusable UI components
│   │   │   ├── NotionCard.tsx
│   │   │   ├── NotionTag.tsx
│   │   │   └── index.ts
│   │   ├── dashboard/          # Dashboard-specific components
│   │   ├── chat/               # Chat analysis components
│   │   └── layout/             # Layout components
│   ├── hooks/                   # Custom React hooks
│   ├── utils/                   # Frontend utilities
│   │   └── styleHelpers.ts     # CSS helper functions
│   ├── types/                   # TypeScript type definitions
│   │   ├── common.ts
│   │   └── dashboard.ts
│   ├── constants/               # Application constants
│   │   ├── colors.ts           # Color definitions
│   │   └── timeRanges.ts       # Time range configs
│   ├── App.tsx                  # Main application component
│   ├── api.ts                   # API client
│   ├── constants.ts             # Mock data constants
│   ├── types.ts                 # Shared type definitions
│   └── index.tsx                # React entry point
│
├── docs/                        # Documentation
│   ├── CLAUDE.md                # Claude Code guidance
│   ├── PROJECT_PROGRESS.md      # Development progress
│   ├── ANALYTICS_MODEL.md       # Analytics documentation
│   ├── API_INTEGRATION_STATUS.md
│   ├── BACKEND_FIXES.md
│   ├── NEXT_STEPS.md
│   ├── PERFORMANCE_OPTIMIZATION_GUIDE.md
│   ├── REFACTORING_PROGRESS.md  # Refactoring tracking
│   └── PROJECT_STRUCTURE.md     # This file
│
├── scripts/                     # Utility scripts
│   ├── start-backend.sh         # Start backend (Linux/Mac)
│   ├── start-backend.bat        # Start backend (Windows)
│   ├── check_data.py            # Data validation
│   ├── check_source_tables.py
│   ├── debug_data.py
│   ├── change_event_time.py
│   ├── run_sql_optimization.py
│   ├── update_procedure_with_refund.py
│   └── verify_view_fixed.py
│
├── examples/                    # Example applications
│   └── AppDemo.tsx              # API integration demo
│
├── tests/                       # Test files
│   ├── api/                     # API endpoint tests
│   │   └── test_api_endpoints.py
│   ├── database/                # Database tests
│   │   └── test_db_connection.py
│   ├── integration/             # Integration tests
│   │   └── test_api_integration.py
│   ├── run_all_tests.py         # Run all tests (Python)
│   ├── run_all_tests.sh        # Run all tests (Bash)
│   └── README.md                # Test documentation
│
├── index.html                   # HTML entry point
├── package.json                 # npm dependencies
├── tsconfig.json                # TypeScript config
├── vite.config.ts               # Vite build config
└── README.md                    # Project overview
```

## Key Principles

### 1. **Separation of Concerns**

- **Backend**: Python/FastAPI with organized modules
- **Frontend**: React/TypeScript with component-based architecture
- **Database**: SQL scripts co-located with database code
- **Scripts**: Utility scripts separated from application code

### 2. **Modularity**

- Each backend module has a single responsibility
- Frontend components organized by feature
- Shared utilities in dedicated directories

### 3. **Security**

- All SQL queries use parameterized statements
- No hardcoded credentials
- Proper error handling throughout

### 4. **Maintainability**

- Clear directory structure
- Consistent naming conventions
- Type definitions in `src/types/`
- Utility functions centralized

## File Naming Conventions

- **Components**: PascalCase (e.g., `NotionCard.tsx`)
- **Utilities**: camelCase (e.g., `styleHelpers.ts`)
- **Python modules**: snake_case (e.g., `buyer_analyzer.py`)
- **Constants**: camelCase (e.g., `colors.ts`, `timeRanges.ts`)

## Import Path Aliases

The project uses Vite path aliases for cleaner imports:

```typescript
import { NotionCard } from '@components/common/NotionCard';
import { getIssueTypeStyles } from '@utils/styleHelpers';
import type { NotionCardProps } from '@types/common';
```

## Development Workflow

### Backend Development

```bash
# Start backend server
./scripts/start-backend.sh  # Linux/Mac
scripts\start-backend.bat   # Windows

# Run utility scripts
python scripts/check_data.py
python scripts/debug_data.py

# Run tests
python tests/run_all_tests.py
```

### Frontend Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build
```

### Testing

```bash
# Run all tests
python tests/run_all_tests.py    # Python version
./tests/run_all_tests.sh         # Bash version

# Run specific test categories
python tests/api/test_api_endpoints.py
python tests/database/test_db_connection.py
python tests/integration/test_api_integration.py
```

For detailed test documentation, see [tests/README.md](../tests/README.md)

## Adding New Features

### New Backend Feature

1. Create/update files in `backend/analytics/` for business logic
2. Add routes in `backend/api/routes.py`
3. Add queries in `backend/database/queries.py`
4. Update types as needed

### New Frontend Component

1. Create component in appropriate `src/components/` subdirectory
2. Add types in `src/types/`
3. Export from index files
4. Use path aliases for imports

### New Utility Script

1. Add to `scripts/` directory
2. Follow naming convention: `verb_noun.py`
3. Include docstring and usage comments

## Documentation

- **Project Overview**: See `README.md`
- **Development Progress**: See `docs/PROJECT_PROGRESS.md`
- **API Documentation**: See `docs/API_INTEGRATION_STATUS.md`
- **Analytics Model**: See `docs/ANALYTICS_MODEL.md`
- **Refactoring**: See `docs/REFACTORING_PROGRESS.md`

## Related Projects

This dashboard is designed to work with the **chat-history-crawler** project, which:

- Crawls chat history from Qianniu Workbench (Taobao/Tmall)
- Stores data in PostgreSQL database
- Uses Playwright for browser automation

Data Flow:

```
Qianniu Workbench → Playwright Crawler → MySQL → This Dashboard
```

---

Last updated: 2025-01-19
