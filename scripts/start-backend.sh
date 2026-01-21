#!/bin/bash
# 启动 SmokeSignal Analytics 后端服务

cd "$(dirname "$0")"
echo "🚀 Starting SmokeSignal Analytics Backend..."
echo "📍 Server: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""

python -m backend.main
