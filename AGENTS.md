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

# Canonical backend entrypoint. It locates the main checkout's .venv and backend/.env.
./scripts/start-backend.sh

# If port 8000 is occupied, keep frontend and backend on the same alternate port.
API_PORT=8001 ./scripts/start-backend.sh
VITE_API_PROXY_TARGET=http://localhost:8001 npm run dev

# Resolve the shared virtualenv correctly from either the main checkout or a worktree.
MAIN_ROOT="$(cd "$(git rev-parse --git-common-dir)/.." && pwd)"
"$MAIN_ROOT/.venv/bin/python" tests/run_all_tests.py
"$MAIN_ROOT/.venv/bin/python" tests/api/test_api_endpoints.py
"$MAIN_ROOT/.venv/bin/python" tests/database/test_db_connection.py
"$MAIN_ROOT/.venv/bin/python" tests/integration/test_api_integration.py
```

Do not use bare `python` or `python3` for this repository. They may resolve to the system interpreter or another project's virtualenv and fail to import FastAPI.

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
