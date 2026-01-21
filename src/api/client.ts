/**
 * API Client for SmokeSignal Backend
 * 连接到 FastAPI 后端 (使用预计算表 - v2 API)
 */

const API_BASE = '/api/v2';

/**
 * 通用错误处理
 */
class APIError extends Error {
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
  getBuyers: async (params: {
    search?: string;
    buyer_type?: 'SMOKER' | 'VIC' | 'BOTH';
    vip_level?: 'V3' | 'V2' | 'V1' | 'V0' | 'Non-VIP';
    channel?: 'DTC' | 'PFS';
    sort_by?: 'last_purchase' | 'l6m_spend' | 'vip_level';
    limit?: number;
    offset?: number;
  } = {}) => {
    const queryParams = new URLSearchParams();
    if (params.search) queryParams.append('search', params.search);
    if (params.buyer_type) queryParams.append('buyer_type', params.buyer_type);
    if (params.vip_level) queryParams.append('vip_level', params.vip_level);
    if (params.channel) queryParams.append('channel', params.channel);
    queryParams.append('sort_by', params.sort_by || 'last_purchase');
    queryParams.append('limit', String(params.limit || 100));
    queryParams.append('offset', String(params.offset || 0));

    const response = await fetch(`${API_BASE}/buyers?${queryParams}`);
    return handleResponse<BuyersListResponse>(response);
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
   */
  getBuyerOrders: async (userNick: string, limit = 50) => {
    const response = await fetch(`${API_BASE}/buyers/${encodeURIComponent(userNick)}/orders?limit=${limit}`);
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
    const response = await fetch(`${API_BASE}/buyers/high-value?min_l6m_spend=${minL6MSpend}&limit=${limit}&offset=${offset}`);
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
  total_l6m_spend: number;
  total_l1y_spend: number;
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
  user_nick: string;
  vip_level: string;
  city: string;
  buyer_type: 'SMOKER' | 'VIC' | 'BOTH';
  channel: 'DTC' | 'PFS';
  historical_ltv: number;
  l6m_spend: number;
  l1y_spend: number;
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
  user_nick: string;
  vip_level: string;
  city: string;
  is_new_customer: boolean;
  buyer_type: 'SMOKER' | 'VIC' | 'BOTH';
  channel: 'DTC' | 'PFS';

  // 历史数据
  historical_ltv: number;
  historical_gmv: number;
  historical_refund: number;
  historical_net_sales: number;
  total_orders: number;

  // 时间段数据
  l6m_spend: number;
  l6m_orders: number;
  l1y_spend: number;
  l1y_orders: number;
  rolling_24m_spend: number;

  // 退款数据
  refund_rate: number;

  // 最近购买
  last_purchase_date: string;
  days_since_last_purchase: number;

  // 聊天指标
  chat_frequency: number;
  last_chat_date: string;
  days_since_last_chat: number;

  // 标签
  churn_risk: '高' | '中' | '低';
  discount_sensitivity: '高度敏感' | '中度敏感' | '低度敏感';
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
  order_id: string;
  date: string;
  amount: number;
  status: 'Completed' | 'Shipped' | 'Refunded' | 'Pending';
  items: string[];
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
