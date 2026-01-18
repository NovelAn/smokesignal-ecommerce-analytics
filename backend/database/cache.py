"""
Simple in-memory cache for buyer list queries
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


class QueryCache:
    """Simple in-memory cache with TTL"""

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize cache

        Args:
            ttl_seconds: Time to live for cache entries (default: 5 minutes)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds

    def _generate_key(self, **kwargs) -> str:
        """Generate cache key from parameters"""
        parts = [f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None]
        return "|".join(parts)

    def get(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Get cached value if exists and not expired"""
        key = self._generate_key(**kwargs)

        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() < entry["expires"]:
                return entry["data"]
            else:
                # Expired, remove from cache
                del self.cache[key]

        return None

    def set(self, data: Dict[str, Any], **kwargs):
        """Cache a value"""
        key = self._generate_key(**kwargs)
        self.cache[key] = {
            "data": data,
            "expires": datetime.now() + timedelta(seconds=self.ttl_seconds)
        }

    def clear(self):
        """Clear all cache"""
        self.cache.clear()

    def cleanup(self):
        """Remove expired entries"""
        now = datetime.now()
        expired_keys = [
            key for key, entry in self.cache.items()
            if now >= entry["expires"]
        ]
        for key in expired_keys:
            del self.cache[key]


# Global cache instance
buyer_list_cache = QueryCache(ttl_seconds=300)  # 5 minutes
