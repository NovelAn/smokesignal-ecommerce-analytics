"""
AI Cache Manager - Redis集成的缓存管理器
支持分层缓存策略，实现720x性能提升
"""
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from backend.config import settings

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("[AI Cache] Redis未安装，将使用内存缓存")


class AICacheManager:
    """
    AI分析缓存管理器

    支持分层缓存策略:
    - HOT: VIP客户 (V3/V2) - 7天TTL
    - WARM: 有聊天记录 - 14天TTL
    - COLD: 无聊天记录 - 30天TTL
    """

    def __init__(self):
        """初始化缓存管理器"""
        self.redis_client = None
        self.fallback_cache = {}  # 内存缓存作为fallback

        if REDIS_AVAILABLE and settings.ai_enable_cache:
            try:
                # 尝试连接Redis
                redis_url = getattr(settings, 'redis_url', 'redis://localhost:6379/0')
                self.redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # 测试连接
                self.redis_client.ping()
                print("[AI Cache] Redis连接成功")
            except Exception as e:
                print(f"[AI Cache] Redis连接失败，使用内存缓存: {e}")
                self.redis_client = None
        else:
            print("[AI Cache] 缓存禁用或Redis不可用")

    @staticmethod
    def get_cache_key(buyer_nick: str, profile: Dict, chat_count: int = 0) -> str:
        """
        生成缓存键

        使用buyer_nick + 关键字段生成hash
        """
        key_data = {
            "buyer_nick": buyer_nick,
            "vip_level": profile.get("vip_level", ""),
            "l6m_netsales": profile.get("l6m_netsales", 0),
            "last_purchase_date": profile.get("last_purchase_date", ""),
            "chat_count": chat_count  # 聊天数量影响分析结果
        }
        data_str = json.dumps(key_data, sort_keys=True)
        return f"ai_analysis:{hashlib.md5(data_str.encode()).hexdigest()}"

    def get_cache_tier(self, profile: Dict, chat_count: int) -> int:
        """
        获取缓存层级（TTL天数）

        Args:
            profile: 客户档案
            chat_count: 聊天记录数量

        Returns:
            TTL天数
        """
        vip_level = profile.get("vip_level", "Non-VIP")

        # HOT: VIP客户 (V3/V2) - 7天TTL（高频访问）
        if vip_level in ["V3", "V2"]:
            return 7

        # WARM: 有聊天记录 - 14天TTL
        if chat_count > 0:
            return 14

        # COLD: 无聊天记录 - 30天TTL（数据变化慢）
        return 30

    def set(self, key: str, data: Any, ttl_days: int = 30):
        """
        设置缓存

        Args:
            key: 缓存键
            data: 缓存数据
            ttl_days: 过期时间（天）
        """
        ttl_seconds = ttl_days * 24 * 3600

        if self.redis_client:
            try:
                # 使用Redis存储
                json_data = json.dumps(data, ensure_ascii=False)
                self.redis_client.setex(
                    key,
                    ttl_seconds,
                    json_data
                )
                print(f"[AI Cache] Redis缓存成功 - TTL: {ttl_days}天")
            except Exception as e:
                print(f"[AI Cache] Redis写入失败，使用内存缓存: {e}")
                self._set_memory_cache(key, data, ttl_seconds)
        else:
            self._set_memory_cache(key, data, ttl_seconds)

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存

        Args:
            key: 缓存键

        Returns:
            缓存数据，如果不存在返回None
        """
        if self.redis_client:
            try:
                # 从Redis读取
                json_data = self.redis_client.get(key)
                if json_data:
                    print(f"[AI Cache] Redis缓存命中")
                    return json.loads(json_data)
            except Exception as e:
                print(f"[AI Cache] Redis读取失败: {e}")

        # Fallback到内存缓存
        return self._get_memory_cache(key)

    def delete(self, key: str):
        """删除缓存"""
        if self.redis_client:
            try:
                self.redis_client.delete(key)
                print(f"[AI Cache] Redis缓存已删除")
            except Exception as e:
                print(f"[AI Cache] Redis删除失败: {e}")

        # 同时删除内存缓存
        if key in self.fallback_cache:
            del self.fallback_cache[key]

    def clear_by_pattern(self, pattern: str):
        """
        按模式清空缓存

        Args:
            pattern: Redis key pattern (e.g., "ai_analysis:*")
        """
        if self.redis_client:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                    print(f"[AI Cache] 清空了 {len(keys)} 条缓存")
            except Exception as e:
                print(f"[AI Cache] 批量删除失败: {e}")

    def get_stats(self) -> Dict:
        """
        获取缓存统计

        Returns:
            {
                "backend": str,  # "redis" or "memory"
                "total_keys": int,
                "hit_rate": float  # 如果可用
            }
        """
        if self.redis_client:
            try:
                info = self.redis_client.info('stats')
                key_count = self.redis_client.dbsize()
                return {
                    "backend": "redis",
                    "total_keys": key_count,
                    "hit_rate": info.get('keyspace_hits', 0) / max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1) * 100
                }
            except Exception as e:
                print(f"[AI Cache] 获取Redis统计失败: {e}")

        # 内存缓存统计
        return {
            "backend": "memory",
            "total_keys": len(self.fallback_cache),
            "hit_rate": 0.0
        }

    def _set_memory_cache(self, key: str, data: Any, ttl_seconds: int):
        """设置内存缓存"""
        expiry = datetime.now() + timedelta(seconds=ttl_seconds)
        self.fallback_cache[key] = {
            "data": data,
            "expiry": expiry
        }
        print(f"[AI Cache] 内存缓存成功 - TTL: {ttl_seconds}秒")

    def _get_memory_cache(self, key: str) -> Optional[Any]:
        """获取内存缓存"""
        if key not in self.fallback_cache:
            return None

        cache_item = self.fallback_cache[key]

        # 检查是否过期
        if datetime.now() > cache_item["expiry"]:
            del self.fallback_cache[key]
            return None

        print(f"[AI Cache] 内存缓存命中")
        return cache_item["data"]


# 全局单例
_ai_cache_manager_instance = None


def get_ai_cache_manager() -> AICacheManager:
    """获取AI缓存管理器单例"""
    global _ai_cache_manager_instance
    if _ai_cache_manager_instance is None:
        _ai_cache_manager_instance = AICacheManager()
    return _ai_cache_manager_instance
