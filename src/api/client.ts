/**
 * API Client for SmokeSignal Backend
 * 连接到 FastAPI 后端 (使用预计算表 - v2 API)
 */

const API_BASE = '/api/v2';
const BUYERS_TIMEOUT_MS = 15000;

type BuyersQueryParams = {
  search?: string;
  buyer_type?: 'SMOKER' | 'VIC' | 'BOTH' | ('SMOKER' | 'VIC' | 'BOTH')[];
  vip_level?: 'V3' | 'V2' | 'V1' | 'V0' | 'Non-VIP' | ('V3' | 'V2' | 'V1' | 'V0' | 'Non-VIP')[];
  channel?: 'DTC' | 'PFS' | ('DTC' | 'PFS')[];
  last_purchase_after?: string;
};

/**
 * 通用错误处理
 */
export class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'APIError';
  }
}

/**
 * API响应包装器
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new APIError(response.status, error.detail || error.message || '请求失败');
  }
  return response.json();
}

/**
 * API客户端
 */
export const apiClient = {
  // ========== Dashboard 相关 ==========

  /**
   * 获取Dashboard汇总指标
   * GET /api/v2/dashboard/metrics
   */
  getDashboardMetrics: async () => {
    const response = await fetch(`${API_BASE}/dashboard/metrics`);
    return handleResponse<DashboardMetrics>(response);
  },

  // ========== 买家列表相关 ==========

  /**
   * 获取所有目标买家列表(分页)
   * GET /api/v2/buyers
   */
  getBuyers: async (params: BuyersQueryParams & {
    sort_by?: 'last_purchase' | 'l6m_netsales' | 'vip_level';
    last_purchase_after?: string;
    limit?: number;
    offset?: number;
  } = {}) => {
    const queryParams = new URLSearchParams();
    if (params.search) queryParams.append('search', params.search);
    if (params.buyer_type) {
      const buyerTypes = Array.isArray(params.buyer_type) ? params.buyer_type : [params.buyer_type];
      buyerTypes.forEach((item) => queryParams.append('buyer_type', item));
    }
    if (params.vip_level) {
      const vipLevels = Array.isArray(params.vip_level) ? params.vip_level : [params.vip_level];
      vipLevels.forEach((item) => queryParams.append('vip_level', item));
    }
    if (params.channel) {
      const channels = Array.isArray(params.channel) ? params.channel : [params.channel];
      channels.forEach((item) => queryParams.append('channel', item));
    }
    if (params.last_purchase_after) queryParams.append('last_purchase_after', params.last_purchase_after);
    queryParams.append('sort_by', params.sort_by || 'last_purchase');
    queryParams.append('limit', String(params.limit || 100));
    queryParams.append('offset', String(params.offset || 0));
    queryParams.append('include_total', 'false');

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), BUYERS_TIMEOUT_MS);
    const response = await fetch(`${API_BASE}/buyers?${queryParams}`, { signal: controller.signal })
      .catch((error) => {
        if (error?.name === 'AbortError') {
          throw new APIError(408, '买家列表请求超时，请检查后端数据库或稍后重试');
        }
        throw error;
      })
      .finally(() => clearTimeout(timeoutId));
    return handleResponse<BuyersListResponse>(response);
  },

  getBuyersCount: async (params: BuyersQueryParams = {}) => {
    const queryParams = new URLSearchParams();
    if (params.buyer_type) {
      const buyerTypes = Array.isArray(params.buyer_type) ? params.buyer_type : [params.buyer_type];
      buyerTypes.forEach((item) => queryParams.append('buyer_type', item));
    }
    if (params.vip_level) {
      const vipLevels = Array.isArray(params.vip_level) ? params.vip_level : [params.vip_level];
      vipLevels.forEach((item) => queryParams.append('vip_level', item));
    }
    if (params.channel) {
      const channels = Array.isArray(params.channel) ? params.channel : [params.channel];
      channels.forEach((item) => queryParams.append('channel', item));
    }
    if (params.last_purchase_after) queryParams.append('last_purchase_after', params.last_purchase_after);
    if (params.search) queryParams.append('search', params.search);
    const response = await fetch(`${API_BASE}/buyers/count?${queryParams}`);
    return handleResponse<BuyersCountResponse>(response);
  },

  /**
   * 获取买家360°详情
   * GET /api/v2/buyers/{user_nick}
   */
  getBuyerProfile: async (userNick: string, includeAI = false) => {
    const params = includeAI ? '?include_ai=true' : '';
    const response = await fetch(`${API_BASE}/buyers/${encodeURIComponent(userNick)}${params}`);
    return handleResponse<BuyerProfile>(response);
  },

  /**
   * 获取买家订单历史
   * GET /api/v2/buyers/{user_nick}/orders
   * @param userNick 买家昵称
   * @param limit 返回数量限制
   * @param timeRange 时间范围: 7d/15d/30d/90d/1y/all (默认 'all' 获取全部历史)
   */
  getBuyerOrders: async (userNick: string, limit = 50, timeRange = 'all') => {
    const response = await fetch(`${API_BASE}/buyers/${encodeURIComponent(userNick)}/orders?limit=${limit}&time_range=${timeRange}`);
    return handleResponse<OrderRecord[]>(response);
  },

  /**
   * 获取买家聊天记录
   * GET /api/v2/buyers/{user_nick}/chats
   */
  getBuyerChats: async (userNick: string, limit = 100) => {
    const response = await fetch(`${API_BASE}/buyers/${encodeURIComponent(userNick)}/chats?limit=${limit}`);
    return handleResponse<ChatMessage[]>(response);
  },

  // ========== 筛选查询相关 ==========

  /**
   * 按买家类型筛选
   * GET /api/v2/buyers/type/{buyer_type}
   */
  getBuyersByType: async (buyerType: 'SMOKER' | 'VIC' | 'BOTH', limit = 100, offset = 0) => {
    const response = await fetch(`${API_BASE}/buyers/type/${buyerType}?limit=${limit}&offset=${offset}`);
    return handleResponse<BuyerInfo[]>(response);
  },

  /**
   * 按VIP等级筛选
   * GET /api/v2/buyers/vip-level/{vip_level}
   */
  getBuyersByVIPLevel: async (vipLevel: 'V3' | 'V2' | 'V1' | 'V0' | 'Non-VIP', limit = 100, offset = 0) => {
    const response = await fetch(`${API_BASE}/buyers/vip-level/${vipLevel}?limit=${limit}&offset=${offset}`);
    return handleResponse<BuyerInfo[]>(response);
  },

  /**
   * 获取VIC买家列表
   * GET /api/v2/buyers/vic
   */
  getVICBuyers: async (limit = 100, offset = 0) => {
    const response = await fetch(`${API_BASE}/buyers/vic?limit=${limit}&offset=${offset}`);
    return handleResponse<BuyerInfo[]>(response);
  },

  /**
   * 获取Smoker买家列表
   * GET /api/v2/buyers/smoker
   */
  getSmokerBuyers: async (limit = 100, offset = 0) => {
    const response = await fetch(`${API_BASE}/buyers/smoker?limit=${limit}&offset=${offset}`);
    return handleResponse<BuyerInfo[]>(response);
  },

  /**
   * 获取流失风险买家
   * GET /api/v2/buyers/churn-risk/{risk_level}
   */
  getChurnRiskBuyers: async (riskLevel: '高' | '中' | '低', limit = 100, offset = 0) => {
    const response = await fetch(`${API_BASE}/buyers/churn-risk/${riskLevel}?limit=${limit}&offset=${offset}`);
    return handleResponse<BuyerInfo[]>(response);
  },

  /**
   * 获取高价值买家
   * GET /api/v2/buyers/high-value
   */
  getHighValueBuyers: async (minL6MSpend = 5000, limit = 100, offset = 0) => {
    const response = await fetch(`${API_BASE}/buyers/high-value?min_l6m_netsales=${minL6MSpend}&limit=${limit}&offset=${offset}`);
    return handleResponse<BuyerInfo[]>(response);
  },

  // ========== 统计数据相关 ==========

  /**
   * 按渠道统计
   * GET /api/v2/stats/channel
   */
  getChannelStats: async () => {
    const response = await fetch(`${API_BASE}/stats/channel`);
    return handleResponse<ChannelStats[]>(response);
  },

  /**
   * 获取需要优先处理的客户
   * GET /api/v2/actionable-customers
   */
  getActionableCustomers: async (limit = 50) => {
    const response = await fetch(`${API_BASE}/actionable-customers?limit=${limit}`);
    return handleResponse<ActionableCustomersResponse>(response);
  },

  /**
   * 强制刷新AI分析
   * POST /api/v2/buyers/{user_nick}/force-refresh
   */
  forceRefreshAnalysis: async (userNick: string, refreshType: 'persona' | 'sentiment' | 'all' = 'all') => {
    const response = await fetch(
      `${API_BASE}/buyers/${encodeURIComponent(userNick)}/force-refresh?refresh_type=${refreshType}`,
      { method: 'POST' }
    );
    return handleResponse<{ buyer_nick: string; refresh_type: string; message: string }>(response);
  },

  // ========== 场外信息相关 ==========

  /**
   * 获取场外记录列表（支持分页和筛选）
   * GET /api/v2/external/records
   */
  getExternalRecords: async (params: {
    search?: string;
    record_type?: 'communication' | 'purchase';
    channel?: string;
    date_from?: string;
    date_to?: string;
    limit?: number;
    offset?: number;
  } = {}) => {
    const queryParams = new URLSearchParams();
    if (params.search) queryParams.append('search', params.search);
    if (params.record_type) queryParams.append('record_type', params.record_type);
    if (params.channel) queryParams.append('channel', params.channel);
    if (params.date_from) queryParams.append('date_from', params.date_from);
    if (params.date_to) queryParams.append('date_to', params.date_to);
    queryParams.append('limit', String(params.limit || 100));
    queryParams.append('offset', String(params.offset || 0));

    const response = await fetch(`${API_BASE}/external/records?${queryParams}`);
    return handleResponse<ExternalRecordsListResponse>(response);
  },

  /**
   * 获取单条场外记录
   * GET /api/v2/external/records/{record_id}
   */
  getExternalRecord: async (recordId: string) => {
    const response = await fetch(`${API_BASE}/external/records/${recordId}`);
    return handleResponse<ExternalRecord>(response);
  },

  /**
   * 创建场外记录
   * POST /api/v2/external/records
   */
  createExternalRecord: async (record: Omit<ExternalRecord, 'id' | 'created_at' | 'updated_at'>) => {
    const response = await fetch(`${API_BASE}/external/records`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(record),
    });
    return handleResponse<ExternalRecord>(response);
  },

  /**
   * 更新场外记录
   * PUT /api/v2/external/records/{record_id}
   */
  updateExternalRecord: async (recordId: string, record: Partial<Omit<ExternalRecord, 'id' | 'created_at' | 'updated_at'>>) => {
    const response = await fetch(`${API_BASE}/external/records/${recordId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(record),
    });
    return handleResponse<ExternalRecord>(response);
  },

  /**
   * 删除场外记录
   * DELETE /api/v2/external/records/{record_id}
   */
  deleteExternalRecord: async (recordId: string) => {
    const response = await fetch(`${API_BASE}/external/records/${recordId}`, {
      method: 'DELETE',
    });
    return handleResponse<{ message: string }>(response);
  },

  /**
   * 获取场外记录统计
   * GET /api/v2/external/statistics
   */
  getExternalRecordsStats: async () => {
    const response = await fetch(`${API_BASE}/external/statistics`);
    return handleResponse<ExternalRecordsStats>(response);
  },

  /**
   * 批量导入场外记录
   * POST /api/v2/external/import
   */
  importExternalRecords: async (file: File, createdBy?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (createdBy) formData.append('created_by', createdBy);

    const response = await fetch(`${API_BASE}/external/import`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<BatchImportResult>(response);
  },

  /**
   * 获取CSV模板URL
   */
  getExternalRecordsTemplate: () => `${API_BASE}/external/export/template`,

  /**
   * 获取指定用户的场外记录
   * GET /api/v2/external/users/{user_nick}
   */
  getExternalRecordsByUser: async (userNick: string, limit = 50) => {
    const response = await fetch(`${API_BASE}/external/users/${encodeURIComponent(userNick)}?limit=${limit}`);
    return handleResponse<ExternalRecord[]>(response);
  },

  // ========== AI 批量分析相关 ==========

  /**
   * 启动批量AI情感/意图分析
   * POST /api/v2/ai/batch-analyze
   */
  startBatchAnalysis: async (buyerLimit: number = 100) => {
    const response = await fetch(
      `${API_BASE}/ai/batch-analyze?buyer_limit=${buyerLimit}`,
      { method: 'POST' }
    );
    return handleResponse<{ task_id: string; status: string; message: string }>(response);
  },

  /**
   * 获取批量分析任务状态
   * GET /api/v2/ai/batch-status/{task_id}
   */
  getBatchAnalysisStatus: async (taskId: string) => {
    const response = await fetch(`${API_BASE}/ai/batch-status/${taskId}`);
    return handleResponse<BatchAnalysisStatus>(response);
  },

  /**
   * 获取情感分析汇总
   * GET /api/v2/analytics/sentiment-summary
   */
  getSentimentSummary: async () => {
    const response = await fetch(`${API_BASE}/analytics/sentiment-summary`);
    return handleResponse<SentimentSummary>(response);
  },

  // ========== Priority Customers 相关 ==========

  /**
   * 获取需优先关注的客户列表
   * GET /api/v2/priority-customers
   */
  getPriorityCustomers: async (params: PriorityCustomersFilters & {
    limit?: number;
    offset?: number;
    include_total?: boolean;
  } = {}) => {
    const queryParams = new URLSearchParams();

    // 处理数组参数
    if (params.channel) {
      params.channel.forEach((c) => queryParams.append('channel', c));
    }
    if (params.buyer_type) {
      params.buyer_type.forEach((t) => queryParams.append('buyer_type', t));
    }
    if (params.follow_priority) {
      params.follow_priority.forEach((p) => queryParams.append('follow_priority', p));
    }
    if (params.sentiment_label) {
      params.sentiment_label.forEach((s) => queryParams.append('sentiment_label', s));
    }
    if (params.has_chat) {
      queryParams.append('has_chat', params.has_chat);
    }

    // 布尔参数
    if (params.use_default_filter !== undefined) {
      queryParams.append('use_default_filter', String(params.use_default_filter));
    }

    // 分页参数
    queryParams.append('limit', String(params.limit || 20));
    queryParams.append('offset', String(params.offset || 0));
    if (params.include_total !== false) {
      queryParams.append('include_total', 'true');
    }

    const response = await fetch(`${API_BASE}/priority-customers?${queryParams}`);
    return handleResponse<PriorityCustomersResponse>(response);
  },

  /**
   * 获取Priority Customers CSV导出URL
   */
  getPriorityCustomersCSVUrl: (params: PriorityCustomersFilters = {}) => {
    const queryParams = new URLSearchParams();

    if (params.channel) {
      params.channel.forEach((c) => queryParams.append('channel', c));
    }
    if (params.buyer_type) {
      params.buyer_type.forEach((t) => queryParams.append('buyer_type', t));
    }
    if (params.follow_priority) {
      params.follow_priority.forEach((p) => queryParams.append('follow_priority', p));
    }
    if (params.sentiment_label) {
      params.sentiment_label.forEach((s) => queryParams.append('sentiment_label', s));
    }
    if (params.has_chat) {
      queryParams.append('has_chat', params.has_chat);
    }
    if (params.use_default_filter !== undefined) {
      queryParams.append('use_default_filter', String(params.use_default_filter));
    }

    return `${API_BASE}/priority-customers/export?${queryParams}`;
  },

  // ========== 关键词分析相关 ==========

  /**
   * 获取关键词分析数据
   * GET /api/v2/keyword-analysis
   */
  getKeywordAnalysis: async (params: KeywordAnalysisParams = {}) => {
    const queryParams = new URLSearchParams();

    if (params.buyer_types && params.buyer_types.length > 0) {
      queryParams.append('buyer_types', params.buyer_types.join(','));
    }
    if (params.category) {
      queryParams.append('category', params.category);
    }
    if (params.limit) {
      queryParams.append('limit', String(params.limit));
    }

    const response = await fetch(`${API_BASE}/keyword-analysis?${queryParams}`);
    return handleResponse<KeywordAnalysisResponse>(response);
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

export interface BuyersCountResponse {
  total: number;
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
  l6m_netsales: number;
  l6m_orders: number;
  l1y_netsales: number;
  l1y_orders: number;
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

  // RFM 分析
  rfm_recency_score: number;       // 1-5分，最近购买时间
  rfm_frequency_score: number;     // 1-5分，购买频次
  rfm_monetary_score: number;      // 1-5分，消费金额
  rfm_segment: string;             // RFM分层结果，如 "Champions", "Loyal Customers" 等

  // AI分析 (如果 include_ai=true)
  ai_analysis?: {
    summary: string;
    key_interests: string[];
    pain_points: string[];
    recommended_action: string;
  };

  // Intent Distribution (from buyer_ai_analysis_cache)
  intent_distribution?: Record<string, number>; // e.g., {"Pre-sale Inquiry": 10, "Post-sale Support": 5}
  ai_dominant_intent?: string; // e.g., "Pre-sale Inquiry"
  sentiment_label?: string; // e.g., "Positive", "Neutral", "Negative"
  sentiment_score?: number; // e.g., 0.8

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

// ========== 场外信息类型定义 ==========

export type ExternalRecordType = 'communication' | 'purchase';

export interface ExternalRecord {
  id: string;
  user_nick: string;
  record_type: ExternalRecordType;
  record_date: string;
  channel: string | null;
  content: string | null;
  notes: string | null;
  amount: number | null;
  category: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExternalRecordsListResponse {
  records: ExternalRecord[];
  total: number;
  limit: number;
  offset: number;
}

export interface ExternalRecordsStats {
  total_records: number;
  communication_count: number;
  purchase_count: number;
  total_offline_amount: number;
  top_channels: Array<{ channel: string; count: number }>;
  recent_records: ExternalRecord[];
}

export interface BatchImportResult {
  success_count: number;
  failed_count: number;
  errors: string[];
  parse_errors?: string[];
}

// ========== 批量分析类型定义 ==========

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

export interface SentimentSummary {
  total_analyzed: number;
  positive: {
    count: number;
    avg_score: number;
  };
  neutral: {
    count: number;
    avg_score: number;
  };
  negative: {
    count: number;
    avg_score: number;
  };
  distribution_percent: {
    positive: number;
    neutral: number;
    negative: number;
  };
}

// ========== Priority Customers 类型定义 ==========

export interface PriorityCustomer {
  buyer_nick: string;
  channel: 'DTC' | 'PFS';
  buyer_type: 'SMOKER' | 'VIC' | 'BOTH';
  vip_level: string;
  rfm_segment: string;
  follow_priority: '紧急' | '高' | '中' | '低';
  sentiment_label: string;
  dominant_intent: string;
  last_purchase_date: string;
  l6m_netsales: number;
  l1y_netsales: number;
  l1y_refund_rate: number;
  has_chat: boolean;
  // AI Persona fields
  persona_key_interests: string[] | null;
  persona_pain_points: string[] | null;
  persona_recommended_action: string | null;
}

export interface PriorityCustomersFilters {
  channel?: ('DTC' | 'PFS')[];
  buyer_type?: ('SMOKER' | 'VIC' | 'BOTH')[];
  follow_priority?: ('紧急' | '高' | '中' | '低')[];
  sentiment_label?: ('Positive' | 'Neutral' | 'Negative')[];
  has_chat?: 'true' | 'false' | 'all';
  use_default_filter?: boolean;
}

export interface PriorityCustomersResponse {
  customers: PriorityCustomer[];
  total: number;
  limit: number;
  offset: number;
}

// ========== 关键词分析类型定义 ==========

export type BuyerTypeForKeyword = 'ALL' | 'SMOKER' | 'BOTH' | 'VIC';

export interface KeywordAnalysisParams {
  buyer_types?: BuyerTypeForKeyword[];
  category?: string;
  limit?: number;
}

export interface KeywordAnalysisCategory {
  name: string;
  value: number;
  percentage: number;
}

export interface KeywordAnalysisKeyword {
  text: string;
  value: number;
  percentage: number;
  category: string;
}

export interface KeywordAnalysisResponse {
  category_distribution: KeywordAnalysisCategory[];
  keywords: KeywordAnalysisKeyword[];
  total_messages: number;
  buyer_types: string[];
  selected_category: string | null;
}
