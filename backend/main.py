"""
SmokeSignal Analytics Backend Service
FastAPI application for buyer analytics and CRM
"""
import sys
import io
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# NOTE: stdout/stderr 的 UTF-8 重包装放在 __main__ 块中执行。
# 模块级执行会破坏 pytest 的 capture（pytest 会替换 sys.stdout，
# 重包装其 buffer 会在 session 拆解时引发 "I/O operation on closed file"）。

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.config import settings
from backend.api import target_router, external_router
from backend.api.insights_routes import router as insights_router
from backend.api.action_routes import router as action_router

# Create FastAPI app
app = FastAPI(
    title="SmokeSignal Analytics API",
    description="Buyer analytics and CRM backend for e-commerce",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(target_router)  # v2.0 routes with /api/v2 prefix
app.include_router(external_router)  # External records routes with /api/v2/external prefix
app.include_router(insights_router)  # Insights routes with /api/v2/insights prefix
app.include_router(action_router)  # Action routes with /api/v2/action prefix

# Serve uploaded files
import os
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "SmokeSignal Analytics Backend",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "api": "/api",
            "docs": "/docs",
            "health": "/api/health"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    # 设置标准输出编码为 UTF-8（仅在直接运行服务时生效）
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    print(f"🚀 Starting SmokeSignal Analytics Backend...")
    print(f"📍 Server: http://{settings.api_host}:{settings.api_port}")
    print(f"📚 API Docs: http://{settings.api_host}:{settings.api_port}/docs")

    reload_enabled = os.getenv("API_RELOAD", "false").lower() == "true"

    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=reload_enabled
    )
