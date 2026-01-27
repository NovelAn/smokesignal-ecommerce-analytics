/**
 * 内存缓存工具
 *
 * 提供简单的内存缓存功能，支持TTL（过期时间）
 * 用于缓存API响应数据，减少重复请求
 */

import { CACHE } from '../constants/cache';

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
}

/**
 * API缓存类
 */
export class APICache {
  private cache = new Map<string, CacheEntry<any>>();
  private cleanupInterval: NodeJS.Timeout | null = null;

  constructor() {
    // 每分钟清理一次过期缓存
    if (typeof window !== 'undefined') {
      this.cleanupInterval = window.setInterval(() => {
        this.cleanup();
      }, 60 * 1000);
    }
  }

  /**
   * 获取缓存数据
   * @param key 缓存键
   * @returns 缓存数据，如果不存在或已过期返回 null
   */
  get<T>(key: string): T | null {
    const entry = this.cache.get(key);

    if (!entry) {
      return null;
    }

    const now = Date.now();
    const age = now - entry.timestamp;

    // 检查是否过期
    if (age > entry.ttl) {
      this.cache.delete(key);
      return null;
    }

    return entry.data;
  }

  /**
   * 设置缓存数据
   * @param key 缓存键
   * @param data 数据
   * @param ttl 过期时间（毫秒），默认使用 CACHE.DEFAULT_TTL
   */
  set<T>(key: string, data: T, ttl = CACHE.DEFAULT_TTL): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl,
    });
  }

  /**
   * 删除指定缓存
   * @param key 缓存键
   */
  delete(key: string): void {
    this.cache.delete(key);
  }

  /**
   * 清空所有缓存
   */
  clear(): void {
    this.cache.clear();
  }

  /**
   * 清理过期缓存
   */
  cleanup(): void {
    const now = Date.now();

    for (const [key, entry] of this.cache.entries()) {
      const age = now - entry.timestamp;
      if (age > entry.ttl) {
        this.cache.delete(key);
      }
    }
  }

  /**
   * 获取缓存统计信息
   */
  getStats() {
    return {
      size: this.cache.size,
      keys: Array.from(this.cache.keys()),
    };
  }

  /**
   * 销毁缓存实例，清理定时器
   */
  destroy(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
    this.clear();
  }
}

/**
 * 全局缓存实例
 */
export const apiCache = new APICache();

/**
 * 带缓存的 fetch 封装
 * @param key 缓存键
 * @param fetchFn 数据获取函数
 * @param ttl 过期时间（毫秒）
 */
export async function fetchWithCache<T>(
  key: string,
  fetchFn: () => Promise<T>,
  ttl?: number
): Promise<T> {
  // 尝试从缓存获取
  const cached = apiCache.get<T>(key);
  if (cached !== null) {
    console.debug(`[Cache Hit] ${key}`);
    return cached;
  }

  console.debug(`[Cache Miss] ${key}`);

  // 缓存未命中，执行请求
  const data = await fetchFn();

  // 存入缓存
  apiCache.set(key, data, ttl);

  return data;
}

/**
 * 预设缓存键生成器
 */
export const cacheKeys = {
  dashboardMetrics: () => 'dashboard:metrics',
  buyersList: (params: Record<string, any> = {}) => {
    const queryString = Object.keys(params)
      .sort()
      .map(key => `${key}=${params[key]}`)
      .join('&');
    return queryString ? `buyers:list?${queryString}` : 'buyers:list';
  },
  buyerDetail: (nick: string) => `buyer:detail:${nick}`,
  buyerOrders: (nick: string, limit = 50) => `buyer:orders:${nick}:${limit}`,
  buyerChats: (nick: string, limit = 100) => `buyer:chats:${nick}:${limit}`,
  channelStats: () => 'stats:channel',
  actionableCustomers: (limit = 50) => `customers:actionable:${limit}`,
};
