"""
API routes for SmokeSignal Analytics backend (v2.0)

Note: v1.0 API routes have been removed.
All endpoints now use the v2.0 target buyer precomputation API.
"""
from .target_routes import router as target_router

__all__ = ["target_router"]
