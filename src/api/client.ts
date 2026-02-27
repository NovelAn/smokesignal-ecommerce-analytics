/**
 * API Client for SmokeSignal Backend
 * 连接到 FastAPI 后端 (使用预计算表 - v2 API)
 *
 * 功能：
 * - 请求取消（AbortController）
 * - 响应缓存
 * - 统一错误处理
 * - 请求日志
 */

import config from '../config/env';
import { fetchWithCache, cacheKeys } from '../utils/cache';
import { logger } from '../utils/logger';
import { CACHE } from '../constants/cache';
import {
  ExternalRecord,
  ExternalRecordsListResponse,
  ExternalRecordsStats,
  BatchImportResult
} from '../types';

const API_BASE = config.apiBaseUrl;

/**
 * 通用 API 错误类
 */
export class APIError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail?: string
  ) {
    super(message);
    this.name = 'APIError';
  }
}

/**
 * API 请求配置
 */
interface RequestConfig {
  signal?: AbortSignal;
  useCache?: boolean;
  cacheTTL?: number;
}

/**
 * API 响应包装器
 * 统一处理响应和错误
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({
      detail: response.statusText
    }));

    const message = error.detail || error.message || '请求失败';
    logger.error(`API Error [${response.status}]:`, message);

    throw new APIError(response.status, message, error.detail);
  }

  return response.json();
}

/**
 * 执行 fetch 请求（支持取消和缓存）
 */
async function fetchRequest<T>(
  url: string,
  options: RequestInit = {},
  config: RequestConfig = {}
): Promise<T> {
  const { signal, useCache = false, cacheTTL } = config;

  // 添加 signal 到 fetch options
  const fetchOptions: RequestInit = {
    ...options,
    signal,
  };

  // 如果启用缓存，尝试从缓存获取
  if (useCache) {
    return fetchWithCache(
      url,
      () => fetch(url, fetchOptions).then(res => handleResponse<T>(res)),
      cacheTTL
    );
  }

  // 直接请求
  const response = await fetch(url, fetchOptions);
  return handleResponse<T>(response);
}

/**
 * API 客户端
 */
export const apiClient = {
  // ========== Dashboard 相关 ==========

  /**
   * 获取Dashboard汇总指标
   * GET /api/v2/dashboard/metrics
   *
   * @param signal - 可选的 AbortSignal，用于取消请求
   */
  getDashboardMetrics: async (signal?: AbortSignal) => {
    const url = `${API_BASE}/dashboard/metrics`;

    return fetchRequest<DashboardMetrics>(url, {}, {
      signal,
      useCache: true, // Dashboard 数据可以缓存
      cacheTTL: CACHE.DASHBOARD_TTL,
    });
  },

  // ========== 买家列表相关 ==========

  /**
   * 获取所有目标买家列表(分页)
   * GET /api/v2/buyers
   */
  getBuyers: async (
    params: {
      search?: string;
      buyer_type?: ('SMOKER' | 'VIC' | 'BOTH')[] | 'SMOKER' | 'VIC' | 'BOTH';
      vip_level?: ('V3' | 'V2' | 'V1' | 'V0' | 'Non-VIP')[] | 'V3' | 'V2' | 'V1' | 'V0' | 'Non-VIP';
      channel?: ('DTC' | 'PFS')[] | 'DTC' | 'PFS';
      last_purchase_after?: string;
      chat_status?: 'chatted' | 'no_chat';
      sort_by?: 'last_purchase' | 'l6m_netsales' | 'vip_level';
      limit?: number;
      offset?: number;
    } = {},
    signal?: AbortSignal
  ) => {
    const queryParams = new URLSearchParams();

    if (params.search) queryParams.append('search', params.search);
    
    if (params.buyer_type) {
      if (Array.isArray(params.buyer_type)) {
        params.buyer_type.forEach(t => queryParams.append('buyer_type', t));
      } else {
        queryParams.append('buyer_type', params.buyer_type);
      }
    }

    if (params.vip_level) {
      if (Array.isArray(params.vip_level)) {
        params.vip_level.forEach(l => queryParams.append('vip_level', l));
      } else {
        queryParams.append('vip_level', params.vip_level);
      }
    }

    if (params.channel) {
      if (Array.isArray(params.channel)) {
        params.channel.forEach(c => queryParams.append('channel', c));
      } else {
        queryParams.append('channel', params.channel);
      }
    }

    if (params.last_purchase_after) {
      queryParams.append('last_purchase_after', params.last_purchase_after);
    }

    if (params.chat_status) {
      queryParams.append('chat_status', params.chat_status);
    }
    
    queryParams.append('sort_by', params.sort_by || 'last_purchase');
    queryParams.append('limit', String(params.limit || 100));
    queryParams.append('offset', String(params.offset || 0));

    const url = `${API_BASE}/buyers?${queryParams}`;

    return fetchRequest<BuyersListResponse>(url, {}, {
      signal,
      useCache: true, // 列表数据可以短期缓存
      cacheTTL: CACHE.BUYERS_LIST_TTL,
    });
  },

  /**
   * 获取买家360°详情
   * GET /api/v2/buyers/{user_nick}
   */
  getBuyerProfile: async (userNick: string, includeAI = false, signal?: AbortSignal) => {
    const params = includeAI ? '?include_ai=true' : '';
    const url = `${API_BASE}/buyers/${encodeURIComponent(userNick)}${params}`;

    // AI 分析不缓存，普通请求缓存
    const useCache = !includeAI;

    return fetchRequest<BuyerProfile>(url, {}, {
      signal,
      useCache,
      cacheTTL: CACHE.BUYER_DETAIL_TTL,
    });
  },

  /**
   * 获取买家订单历史
   * GET /api/v2/buyers/{user_nick}/orders
   */
  getBuyerOrders: async (userNick: string, limit = 50, timeRange = '1y', signal?: AbortSignal) => {
    const url = `${API_BASE}/buyers/${encodeURIComponent(userNick)}/orders?limit=${limit}&time_range=${timeRange}`;

    return fetchRequest<OrderRecord[]>(url, {}, {
      signal,
      useCache: true,
      cacheTTL: CACHE.MEDIUM_TTL,
    });
  },

  /**
   * 获取买家聊天记录
   * GET /api/v2/buyers/{user_nick}/chats
   */
  getBuyerChats: async (userNick: string, limit = 100, signal?: AbortSignal) => {
    const url = `${API_BASE}/buyers/${encodeURIComponent(userNick)}/chats?limit=${limit}`;

    return fetchRequest<ChatMessage[]>(url, {}, {
      signal,
      useCache: true,
      cacheTTL: CACHE.SHORT_TTL, // 聊天数据变化较快，短期缓存
    });
  },

  // ========== 筛选查询相关 ==========

  /**
   * 按买家类型筛选
   * GET /api/v2/buyers/type/{buyer_type}
   */
  getBuyersByType: async (
    buyerType: 'SMOKER' | 'VIC' | 'BOTH',
    limit = 100,
    offset = 0,
    signal?: AbortSignal
  ) => {
    const url = `${API_BASE}/buyers/type/${buyerType}?limit=${limit}&offset=${offset}`;

    return fetchRequest<BuyerInfo[]>(url, {}, {
      signal,
      useCache: true,
      cacheTTL: CACHE.BUYERS_LIST_TTL,
    });
  },

  /**
   * 按VIP等级筛选
   * GET /api/v2/buyers/vip-level/{vip_level}
   */
  getBuyersByVIPLevel: async (
    vipLevel: 'V3' | 'V2' | 'V1' | 'V0' | 'Non-VIP',
    limit = 100,
    offset = 0,
    signal?: AbortSignal
  ) => {
    const url = `${API_BASE}/buyers/vip-level/${vipLevel}?limit=${limit}&offset=${offset}`;

    return fetchRequest<BuyerInfo[]>(url, {}, {
      signal,
      useCache: true,
      cacheTTL: CACHE.BUYERS_LIST_TTL,
    });
  },

  /**
   * 获取VIC买家列表
   * GET /api/v2/buyers/vic
   */
  getVICBuyers: async (limit = 100, offset = 0, signal?: AbortSignal) => {
    const url = `${API_BASE}/buyers/vic?limit=${limit}&offset=${offset}`;

    return fetchRequest<BuyerInfo[]>(url, {}, {
      signal,
      useCache: true,
      cacheTTL: CACHE.BUYERS_LIST_TTL,
    });
  },

  /**
   * 获取Smoker买家列表
   * GET /api/v2/buyers/smoker
   */
  getSmokerBuyers: async (limit = 100, offset = 0, signal?: AbortSignal) => {
    const url = `${API_BASE}/buyers/smoker?limit=${limit}&offset=${offset}`;

    return fetchRequest<BuyerInfo[]>(url, {}, {
      signal,
      useCache: true,
      cacheTTL: CACHE.BUYERS_LIST_TTL,
    });
  },

  /**
   * 获取流失风险买家
   * GET /api/v2/buyers/churn-risk/{risk_level}
   */
  getChurnRiskBuyers: async (
    riskLevel: '高' | '中' | '低',
    limit = 100,
    offset = 0,
    signal?: AbortSignal
  ) => {
    const url = `${API_BASE}/buyers/churn-risk/${riskLevel}?limit=${limit}&offset=${offset}`;

    return fetchRequest<BuyerInfo[]>(url, {}, {
      signal,
      useCache: true,
      cacheTTL: CACHE.BUYERS_LIST_TTL,
    });
  },

  /**
   * 获取高价值买家
   * GET /api/v2/buyers/high-value
   */
  getHighValueBuyers: async (
    minL6MSpend = 5000,
    limit = 100,
    offset = 0,
    signal?: AbortSignal
  ) => {
    const url = `${API_BASE}/buyers/high-value?min_l6m_netsales=${minL6MSpend}&limit=${limit}&offset=${offset}`;

    return fetchRequest<BuyerInfo[]>(url, {}, {
      signal,
      useCache: true,
      cacheTTL: CACHE.BUYERS_LIST_TTL,
    });
  },

  // ========== 统计数据相关 ==========

  /**
   * 按渠道统计
   * GET /api/v2/stats/channel
   */
  getChannelStats: async (signal?: AbortSignal) => {
    const url = `${API_BASE}/stats/channel`;

    return fetchRequest<ChannelStats[]>(url, {}, {
      signal,
      useCache: true,
      cacheTTL: CACHE.STATS_TTL,
    });
  },

  /**
   * 获取需要优先处理的客户
   * GET /api/v2/actionable-customers
   */
  getActionableCustomers: async (limit = 50, signal?: AbortSignal) => {
    const url = `${API_BASE}/actionable-customers?limit=${limit}`;

    return fetchRequest<ActionableCustomersResponse>(url, {}, {
      signal,
      useCache: true,
      cacheTTL: CACHE.BUYERS_LIST_TTL,
    });
  },

  /**
   * 获取 API Base URL
   */
  getBaseUrl: () => API_BASE,

  // ========== 场外信息相关 ==========

  /**
   * 获取场外记录列表
   * GET /api/v2/external/records
   */
  getExternalRecords: async (
    params: {
      search?: string;
      record_type?: 'communication' | 'purchase';
      channel?: string;
      date_from?: string;
      date_to?: string;
      limit?: number;
      offset?: number;
    } = {},
    signal?: AbortSignal
  ) => {
    const queryParams = new URLSearchParams();

    if (params.search) queryParams.append('search', params.search);
    if (params.record_type) queryParams.append('record_type', params.record_type);
    if (params.channel) queryParams.append('channel', params.channel);
    if (params.date_from) queryParams.append('date_from', params.date_from);
    if (params.date_to) queryParams.append('date_to', params.date_to);
    queryParams.append('limit', String(params.limit || 100));
    queryParams.append('offset', String(params.offset || 0));

    const url = `${API_BASE}/external/records?${queryParams}`;

    return fetchRequest<ExternalRecordsListResponse>(url, {}, {
      signal,
      useCache: false, // 不缓存，确保数据实时
    });
  },

  /**
   * 获取单条场外记录
   * GET /api/v2/external/records/{id}
   */
  getExternalRecord: async (id: string, signal?: AbortSignal) => {
    const url = `${API_BASE}/external/records/${id}`;

    return fetchRequest<ExternalRecord>(url, {}, { signal });
  },

  /**
   * 创建场外记录
   * POST /api/v2/external/records
   */
  createExternalRecord: async (record: Partial<ExternalRecord>, signal?: AbortSignal) => {
    const url = `${API_BASE}/external/records`;

    return fetchRequest<ExternalRecord>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(record),
      signal,
    }, {});
  },

  /**
   * 更新场外记录
   * PUT /api/v2/external/records/{id}
   */
  updateExternalRecord: async (id: string, record: Partial<ExternalRecord>, signal?: AbortSignal) => {
    const url = `${API_BASE}/external/records/${id}`;

    return fetchRequest<ExternalRecord>(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(record),
      signal,
    }, {});
  },

  /**
   * 删除场外记录
   * DELETE /api/v2/external/records/{id}
   */
  deleteExternalRecord: async (id: string, signal?: AbortSignal) => {
    const url = `${API_BASE}/external/records/${id}`;

    return fetchRequest<{ success: boolean; message: string }>(url, {
      method: 'DELETE',
      signal,
    }, {});
  },

  /**
   * 批量导入场外记录
   * POST /api/v2/external/import
   */
  importExternalRecords: async (file: File, createdBy?: string, signal?: AbortSignal) => {
    const formData = new FormData();
    formData.append('file', file);

    const params = createdBy ? `?created_by=${encodeURIComponent(createdBy)}` : '';
    const url = `${API_BASE}/external/import${params}`;

    return fetchRequest<BatchImportResult>(url, {
      method: 'POST',
      body: formData,
      signal,
    }, {});
  },

  /**
   * 获取导入模板
   * GET /api/v2/external/export/template
   */
  getExternalRecordsTemplate: () => {
    return `${API_BASE}/external/export/template`;
  },

  /**
   * 获取场外信息统计
   * GET /api/v2/external/statistics
   */
  getExternalRecordsStats: async (signal?: AbortSignal) => {
    const url = `${API_BASE}/external/statistics`;

    return fetchRequest<ExternalRecordsStats>(url, {}, {
      signal,
      useCache: true,
      cacheTTL: CACHE.SHORT_TTL,
    });
  },

  /**
   * 获取某客户的场外记录
   * GET /api/v2/external/users/{user_nick}
   */
  getUserExternalRecords: async (userNick: string, limit = 50, signal?: AbortSignal) => {
    const url = `${API_BASE}/external/users/${encodeURIComponent(userNick)}?limit=${limit}`;

    return fetchRequest<ExternalRecord[]>(url, {}, { signal });
  },

  // ========== AI 批量分析相关 ==========

  /**
   * 启动批量情感/意图分析
   * POST /api/v2/ai/batch-analyze
   */
  startBatchAnalysis: async (buyerLimit = 200, signal?: AbortSignal) => {
    const url = `${API_BASE}/ai/batch-analyze?buyer_limit=${buyerLimit}`;

    return fetchRequest<BatchAnalysisStartResponse>(url, {
      method: 'POST',
      signal,
    }, {});
  },

  /**
   * 查询批量分析任务状态
   * GET /api/v2/ai/batch-status/{task_id}
   */
  getBatchAnalysisStatus: async (taskId: string, signal?: AbortSignal) => {
    const url = `${API_BASE}/ai/batch-status/${taskId}`;

    return fetchRequest<BatchAnalysisStatus>(url, {}, { signal });
  },

  /**
   * 获取情感分析汇总
   * GET /api/v2/analytics/sentiment-summary
   */
  getSentimentSummary: async (signal?: AbortSignal) => {
    const url = `${API_BASE}/analytics/sentiment-summary`;

    return fetchRequest<SentimentSummary>(url, {}, {
      signal,
      useCache: true,
      cacheTTL: CACHE.SHORT_TTL,
    });
  },

  /**
   * 获取意图分析汇总
   * GET /api/v2/analytics/intent-summary
   */
  getIntentSummary: async (signal?: AbortSignal) => {
    const url = `${API_BASE}/analytics/intent-summary`;

    return fetchRequest<IntentSummary>(url, {}, {
      signal,
      useCache: true,
      cacheTTL: CACHE.SHORT_TTL,
    });
  },

  /**
   * 强制刷新单个客户的AI分析
   * POST /api/v2/buyers/{user_nick}/force-refresh
   */
  forceRefreshAnalysis: async (
    userNick: string,
    refreshType: 'persona' | 'sentiment' | 'all' = 'all',
    signal?: AbortSignal
  ) => {
    const url = `${API_BASE}/buyers/${encodeURIComponent(userNick)}/force-refresh?refresh_type=${refreshType}`;

    return fetchRequest<{ buyer_nick: string; refresh_type: string; message: string }>(url, {
      method: 'POST',
      signal,
    }, {});
  },
};

// ========== TypeScript 类型定义 ==========

/**
 * Dashboard汇总指标
 */
export interface DashboardMetrics {
  total_target_buyers: number;
  total_smokers: number;
  total_vics: number;
  both_smoker_vic: number;
  total_netsales: number;
  avg_netsales: number;
  total_l6m_netsales: number;
  total_l1y_netsales: number;
  total_orders: number;
  avg_orders_per_buyer: number;
  avg_refund_rate: number;
  v3_count: number;
  v2_count: number;
  v1_count: number;
  v0_count: number;
  non_vip_count: number;
  dtc_count: number;
  pfs_count: number;
  high_churn_count: number;
  medium_churn_count: number;
  low_churn_count: number;
  high_discount_count: number;
  medium_discount_count: number;
  low_discount_count: number;
  last_updated: string;
}

/**
 * 买家列表响应
 */
export interface BuyersListResponse {
  buyers: BuyerInfo[];
  total: number | null;
  limit: number;
  offset: number;
}

/**
 * 买家基本信息
 */
export interface BuyerInfo {
  buyer_nick: string;
  vip_level: string;
  city: string;
  buyer_type: 'SMOKER' | 'VIC' | 'BOTH';
  channel: 'DTC' | 'PFS';
  historical_net_sales: number;
  l6m_netsales: number;
  l1y_netsales: number;
  total_orders: number;
  last_purchase_date: string;
  churn_risk: '高' | '中' | '低';
  discount_sensitivity: '高度敏感' | '中度敏感' | '低度敏感';
  top_category: string;
}

/**
 * 买家完整档案
 */
export interface BuyerProfile {
  buyer_nick: string;
  vip_level: string;
  city: string;
  client_monthly_tag: 'new' | 'old';
  buyer_type: 'SMOKER' | 'VIC' | 'BOTH';
  channel: 'DTC' | 'PFS';

  // 历史数据
  historical_gmv: number;
  historical_refund: number;
  historical_net_sales: number;
  total_orders: number;
  total_net_orders: number;
  refund_rate: number;

  // 时间段数据
  l6m_gmv: number;
  l6m_netsales: number;
  l6m_orders: number;
  l6m_refund_rate: number;
  l1y_gmv: number;
  l1y_netsales: number;
  l1y_orders: number;
  l1y_refund_rate: number;
  rolling_24m_netsales: number;
  rolling_24m_orders: number;

  // 折扣相关
  discount_ratio: number;
  discount_sensitivity: '高度敏感' | '中度敏感' | '低度敏感';

  // 最近购买
  first_purchase_date: string;
  last_purchase_date: string;

  // 聊天指标
  chat_frequency_days: number;
  first_chat_date: string | null;
  last_chat_date: string | null;
  l30d_chat_frequency_days: number;
  l3m_chat_frequency_days: number;
  avg_chat_interval_days: number;

  // 标签
  churn_risk: '高' | '中' | '低';
  top_category: string;
  second_category: string;
  third_category: string;

  // AI分析 (如果 include_ai=true)
  ai_analysis?: {
    summary: string;
    key_interests: string[];
    pain_points: string[];
    recommended_action: string;
  };

  // 更新时间
  updated_at: string;
}

/**
 * 订单记录
 */
export interface OrderRecord {
  订单号: string;
  子订单号: string;
  商品名称: string;
  category: string;
  成交总金额: number;
  退款金额: number | null;
  退款类型: string | null;
  FP_MD: string;
  图片地址: string;
  最后付款时间: string;
  件数: number;
  netsales: number;
}

/**
 * 聊天消息
 */
export interface ChatMessage {
  id: string;
  user_nick: string;
  sender_nick: string;
  msg_time: string;
  msg_type: 'text' | 'image' | 'system';
  content: string;
}

/**
 * 渠道统计
 */
export interface ChannelStats {
  channel: 'DTC' | 'PFS';
  total_buyers: number;
  total_ltv: number;
  avg_ltv: number;
}

/**
 * 可操作客户响应
 */
export interface ActionableCustomersResponse {
  high_churn_risk: BuyerInfo[];
  high_value: BuyerInfo[];
  medium_churn_risk: BuyerInfo[];
}

/**
 * 批量分析启动响应
 */
export interface BatchAnalysisStartResponse {
  task_id: string;
  status: 'pending';
  message: string;
}

/**
 * 批量分析任务状态
 */
export interface BatchAnalysisStatus {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  total_buyers: number;
  processed_buyers: number;
  skipped_buyers: number;
  failed_buyers: number;
  progress_percent: number;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

/**
 * 情感分析汇总
 */
export interface SentimentSummary {
  total_analyzed: number;
  positive: { count: number; avg_score: number };
  neutral: { count: number; avg_score: number };
  negative: { count: number; avg_score: number };
  distribution_percent: {
    positive: number;
    neutral: number;
    negative: number;
  };
}

/**
 * 意图分析汇总
 */
export interface IntentSummary {
  total_analyzed: number;
  intents: {
    'Pre-sale Inquiry': number;
    'Post-sale Support': number;
    'Logistics': number;
    'Usage Guide': number;
    'Complaint': number;
  };
}
