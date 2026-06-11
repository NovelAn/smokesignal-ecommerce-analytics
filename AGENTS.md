# AGENTS.md

## Project

SmokeSignal Analytics: Notion-style CRM dashboard for ecommerce customer service analytics, customer sentiment, chat history, purchase behavior, and AI-powered customer insights.

Codex should treat `CLAUDE.md` as the detailed project reference and follow the same v2 API and data safety preferences.

## Common Commands

```bash
npm install
npm run dev
npm run build
npm run preview
./scripts/start-backend.sh
python -m backend.main
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
python tests/run_all_tests.py
python tests/api/test_api_endpoints.py
python tests/database/test_db_connection.py
python tests/integration/test_api_integration.py
```

## Architecture Notes

- Frontend: React, TypeScript, Vite, Recharts.
- Backend: FastAPI with MySQL/PostgreSQL.
- AI: Zhipu AI for customer persona analysis.
- Data source: Qianniu/Taobao/Tmall crawler data.
- Prefer `/api/v2/*` backed by `target_buyers_precomputed` for new development.

## Development Rules

- Do not modify database credentials, AI keys, or local config without explicit confirmation.
- Put new SQL in `backend/database/sql/`, not inline in Python.
- Use `[[OPTIONAL_CONDITION]]` style for dynamic SQL where the existing query loader expects it.
- Test schema or data updates on non-production data first.
- Prefer v2 APIs for performance unless a feature only exists in v1.

## Working Notes

- Keep backend modules feature-based.
- Preserve the current Notion-style dashboard language unless redesign is requested.
- Validate both frontend build and relevant backend tests when touching cross-stack behavior.
