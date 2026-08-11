---
category: 开发指南
title: 快速启动指南
tags: ['快速开始', '开发环境', 'worktree']
description: 从主仓库或 Git worktree 启动 SmokeSignal Analytics
priority: high
last_updated: 2026-08-03
---

# SmokeSignal Analytics 快速启动

## 最快启动

在当前 checkout 或 worktree 根目录运行：

```bash
./scripts/start-backend.sh
```

脚本会自动：

- 找到主仓库的 `.venv`，不依赖当前 shell 的 `python`。
- 加载主仓库的 `backend/.env`。
- 使用当前 checkout 或 worktree 的代码启动 FastAPI。

不要使用下面的命令：

```bash
python -m backend.main
python3 -m backend.main
```

它们可能调用系统 Python 或其他项目的虚拟环境，出现 `ModuleNotFoundError: No module named 'fastapi'`。

## 端口被占用

默认后端端口是 `8000`。先检查：

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

不停止现有服务时，给 SmokeSignal 指定其他端口：

```bash
API_PORT=8001 ./scripts/start-backend.sh
```

后端地址变为：

- API：http://localhost:8001/api/v2/
- API 文档：http://localhost:8001/docs

## 启动前端

前端使用 Node.js 20 或更高版本；先运行 `node --version` 确认。

后端使用默认 `8000` 时：

```bash
npm run dev
```

后端使用 `8001` 时，前端代理必须使用同一个端口：

```bash
VITE_API_PROXY_TARGET=http://localhost:8001 npm run dev
```

前端地址：http://localhost:3000

## AI Analysis V2 worktree

V2 当前位于独立 worktree：

```bash
cd /Users/novel/Projects/smokesignal-ecommerce-analytics/worktrees/ai-analysis-v2
./scripts/start-backend.sh
```

端口 `8000` 被占用时：

```bash
cd /Users/novel/Projects/smokesignal-ecommerce-analytics/worktrees/ai-analysis-v2
API_PORT=8001 ./scripts/start-backend.sh
```

运行前确认分支：

```bash
git status --short --branch
```

V2 worktree 应显示：

```text
## codex/ai-analysis-v2
```

## 验证服务

默认端口：

```bash
curl http://localhost:8000/api/v2/
curl -I http://localhost:8000/docs
```

备用端口：

```bash
curl http://localhost:8001/api/v2/
curl -I http://localhost:8001/docs
```

健康响应应包含：

```json
{
  "status": "ok",
  "service": "SmokeSignal Analytics API v2 (Optimized)",
  "version": "2.0.0"
}
```

## 第一次配置

如果主仓库还没有虚拟环境：

```bash
cd /Users/novel/Projects/smokesignal-ecommerce-analytics
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
```

运行配置放在主仓库：

```text
/Users/novel/Projects/smokesignal-ecommerce-analytics/backend/.env
~/database_config.json
```

不要把 API Key、数据库密码或 `.env` 提交到 Git。

## 运行测试

从主仓库或任意 worktree 获取共享 Python：

```bash
MAIN_ROOT="$(cd "$(git rev-parse --git-common-dir)/.." && pwd)"
PYTHON="$MAIN_ROOT/.venv/bin/python"
```

然后运行：

```bash
"$PYTHON" -m pytest -q tests/ai/test_ai_analysis_v2_*.py
npm run build
```

## 常见故障

### FastAPI 未安装

症状：

```text
ModuleNotFoundError: No module named 'fastapi'
```

原因：调用了错误的 Python。使用：

```bash
./scripts/start-backend.sh
```

### Address already in use

症状：

```text
[Errno 48] Address already in use
```

使用备用端口：

```bash
API_PORT=8001 ./scripts/start-backend.sh
```

### 前端能打开但接口失败

检查前后端端口是否一致：

```bash
API_PORT=8001 ./scripts/start-backend.sh
VITE_API_PROXY_TARGET=http://localhost:8001 npm run dev
```

## 进一步阅读

- [项目开发说明](./CLAUDE.md)
- [Codex 项目规则](./AGENTS.md)
- [AI Analysis V2 设计](./docs/superpowers/specs/2026-07-22-ai-analysis-v2-design.md)
- [部署与回滚](./docs/部署运维/AI_Analysis_V2_部署与回滚.md)
