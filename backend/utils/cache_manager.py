"""
Cache Manager - 缓存管理器
用于缓存AI分析结果，减少API调用成本
"""
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


class CacheManager:
    """
    缓存管理器

    简化实现：使用内存缓存
    完整实现：应该使用Redis
    """

    def __init__(self):
        """初始化缓存管理器"""
        # 内存缓存：{cache_key: {data, expiry}}
        self._cache: Dict[str, Dict] = {}

    @staticmethod
    def get_cache_key(buyer_nick: str, profile: Dict) -> str:
        """
        生成缓存键

        使用buyer_nick + 关键字段生成hash
        """
        key_data = {
            "buyer_nick": buyer_nick,
            "vip_level": profile.get("vip_level", ""),
            "l6m_netsales": profile.get("l6m_netsales", 0),
            "last_purchase_date": profile.get("last_purchase_date", "")
        }
        data_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()

    def set(self, key: str, data: Any, ttl_seconds: int = 30 * 24 * 3600):
        """
        设置缓存

        Args:
            key: 缓存键
            data: 缓存数据
            ttl_seconds: 过期时间（秒），默认30天
        """
        expiry = datetime.now() + timedelta(seconds=ttl_seconds)

        self._cache[key] = {
            "data": data,
            "expiry": expiry
        }

        print(f"[缓存] 已缓存 - 过期时间: {expiry.strftime('%Y-%m-%d %H:%M')}")

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存

        Args:
            key: 缓存键

        Returns:
            缓存数据，如果不存在或已过期返回None
        """
        if key not in self._cache:
            return None

        cache_item = self._cache[key]

        # 检查是否过期
        if datetime.now() > cache_item["expiry"]:
            # 已过期，删除
            del self._cache[key]
            print(f"[缓存] 已过期并删除")
            return None

        print(f"[缓存] 命中")
        return cache_item["data"]

    def delete(self, key: str):
        """删除缓存"""
        if key in self._cache:
            del self._cache[key]
            print(f"[缓存] 已删除")

    def clear_all(self):
        """清空所有缓存"""
        count = len(self._cache)
        self._cache.clear()
        print(f"[缓存] 已清空 {count} 条记录")

    def get_stats(self) -> Dict:
        """
        获取缓存统计

        Returns:
            {
                "total_keys": int,
                "valid_keys": int,
                "expired_keys": int
            }
        """
        now = datetime.now()
        valid_keys = 0
        expired_keys = 0

        for key, item in self._cache.items():
            if now > item["expiry"]:
                expired_keys += 1
            else:
                valid_keys += 1

        return {
            "total_keys": len(self._cache),
            "valid_keys": valid_keys,
            "expired_keys": expired_keys
        }

    def cleanup_expired(self):
        """清理过期的缓存"""
        now = datetime.now()
        expired_keys = [
            key for key, item in self._cache.items()
            if now > item["expiry"]
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            print(f"[缓存] 清理了 {len(expired_keys)} 条过期记录")

        return len(expired_keys)


# 全局单例
_cache_manager_instance = None


def get_cache_manager() -> CacheManager:
    """获取缓存管理器单例"""
    global _cache_manager_instance
    if _cache_manager_instance is None:
        _cache_manager_instance = CacheManager()
    return _cache_manager_instance
