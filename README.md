<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# SmokeSignal E-Commerce Analytics

A Notion-style CRM dashboard for e-commerce customer service analytics. Visualizes customer sentiment, chat history, purchase behavior, and AI-powered customer insights.

**View your app in AI Studio:** https://ai.studio/apps/drive/14aS21FRXtWxJc9UKqX5inwFDswfXQW6t

## Features

- 🎯 **360° Customer Profiles** - Comprehensive buyer analytics with LTV, purchase patterns, and engagement metrics
- 💬 **Chat History Analysis** - Complete communication history with sentiment tracking
- 🤖 **AI-Powered Insights** - Customer persona analysis using Zhipu AI
- 📊 **Interactive Dashboards** - Real-time metrics, keyword analysis, and actionable customer lists
- 🎨 **Notion-Style UI** - Clean, professional interface with familiar design patterns

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
- **Zhipu AI** for customer analysis
- **Playwright** integration for data crawling

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
   # Create .env.local with your API keys
   echo "GEMINI_API_KEY=your_key_here" > .env.local
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
├── src/              # React frontend source
├── docs/             # Documentation
├── scripts/          # Utility scripts
├── examples/         # Example applications
└── tests/            # Test files
```

For detailed structure, see [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)

## Documentation

- **[Project Structure](docs/PROJECT_STRUCTURE.md)** - Complete directory organization
- **[Development Progress](docs/PROJECT_PROGRESS.md)** - What's been built
- **[Analytics Model](docs/ANALYTICS_MODEL.md)** - Customer analytics methodology
- **[API Integration](docs/API_INTEGRATION_STATUS.md)** - Backend API documentation
- **[Performance Guide](docs/PERFORMANCE_OPTIMIZATION_GUIDE.md)** - Optimization tips
- **[Claude Guidance](docs/CLAUDE.md)** - For AI-assisted development

## Key Components

### Dashboard
- **Metrics Overview** - Total conversations, sentiment score, urgent issues
- **Keyword Analysis** - Category distribution and top keywords with time filtering
- **Actionable Customers** - Priority board for churn risk, high-value customers
- **Trend Charts** - Sentiment, intent distribution, peak hours

### Customer 360° Profile
- **AI Persona Analysis** - Summary, key interests, pain points
- **Financial Metrics** - LTV, AOV, discount sensitivity
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

- ✅ **SQL Injection Protection** - All queries use parameterized statements
- ✅ **Error Handling** - Specific exception types with proper logging
- ✅ **Type Safety** - Full TypeScript coverage on frontend
- ✅ **Environment Variables** - Sensitive data in .env files

See [docs/REFACTORING_PROGRESS.md](docs/REFACTORING_PROGRESS.md) for details.

## Related Projects

This dashboard integrates with **chat-history-crawler**, a Playwright-based crawler that:
- Crawls chat history from Qianniu Workbench (Taobao/Tmall)
- Intercepts network responses for data extraction
- Stores data in PostgreSQL database

Data Flow:
```
Qianniu Workbench → Playwright Crawler → PostgreSQL → This Dashboard
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
- Review [PROJECT_PROGRESS.md](docs/PROJECT_PROGRESS.md) for known issues
- Open an issue on GitHub

---

**Built with ❤️ using Google AI Studio**

