"""
SmokeSignal Analytics Backend Service
FastAPI application for buyer analytics and CRM
"""
import sys
import io

# 设置标准输出编码为 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.api import router

# Create FastAPI app
app = FastAPI(
    title="SmokeSignal Analytics API",
    description="Buyer analytics and CRM backend for e-commerce",
    version="1.0.0"
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
app.include_router(router, prefix="/api")


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

    print(f"🚀 Starting SmokeSignal Analytics Backend...")
    print(f"📍 Server: http://{settings.api_host}:{settings.api_port}")
    print(f"📚 API Docs: http://{settings.api_host}:{settings.api_port}/docs")

    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
