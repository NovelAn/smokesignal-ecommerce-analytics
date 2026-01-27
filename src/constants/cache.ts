/**
 * 缓存相关常量
 */

export const CACHE = {
  /** 默认缓存时间（5分钟） */
  DEFAULT_TTL: 5 * 60 * 1000,

  /** 短期缓存（1分钟） - 用于频繁变化的数据 */
  SHORT_TTL: 1 * 60 * 1000,

  /** 中期缓存（15分钟） */
  MEDIUM_TTL: 15 * 60 * 1000,

  /** 长期缓存（1小时） - 用于静态数据 */
  LONG_TTL: 60 * 60 * 1000,

  /** Dashboard指标缓存（30分钟 - 每日更新） */
  DASHBOARD_TTL: 30 * 60 * 1000,

  /** 用户列表缓存（5分钟） */
  BUYERS_LIST_TTL: 5 * 60 * 1000,

  /** 用户详情缓存（10分钟） */
  BUYER_DETAIL_TTL: 10 * 60 * 1000,

  /** 统计数据缓存（15分钟） */
  STATS_TTL: 15 * 60 * 1000,
} as const;

/**
 * 缓存键前缀
 */
export const CACHE_KEYS = {
  /** Dashboard指标 */
  DASHBOARD_METRICS: 'dashboard:metrics',

  /** 买家列表 */
  BUYERS_LIST: 'buyers:list',

  /** 买家详情 */
  BUYER_DETAIL: 'buyer:detail',

  /** 买家订单 */
  BUYER_ORDERS: 'buyer:orders',

  /** 买家聊天 */
  BUYER_CHATS: 'buyer:chats',

  /** 渠道统计 */
  CHANNEL_STATS: 'stats:channel',

  /** 可操作客户 */
  ACTIONABLE_CUSTOMERS: 'customers:actionable',
} as const;

/**
 * 生成缓存键
 * @param prefix 缓存键前缀
 * @param params 参数对象
 */
export function generateCacheKey(
  prefix: string,
  params: Record<string, any> = {}
): string {
  const queryString = Object.keys(params)
    .sort()
    .map(key => `${key}=${JSON.stringify(params[key])}`)
    .join('&');

  return queryString ? `${prefix}?${queryString}` : prefix;
}
