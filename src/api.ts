/**
 * API Client for SmokeSignal Analytics Backend
 * Connects to FastAPI backend at http://localhost:8000
 */

const API_BASE_URL = 'http://localhost:8000/api';

// Types for API responses
export interface BuyerListResponse {
  buyers: string[];
  total: number;
  limit: number;
  offset: number;
}

export interface BuyerProfile {
  user_nick: string;
  profile: {
    city: string;
    is_new_customer: boolean;
    historical_ltv: number;
    total_orders: number;
    discount_ratio: number;
    l6m_spend: number;
    l6m_frequency: number;
    tags: string[];
    intent_scores: Array<{
      subject: string;
      A: number;
      fullMark: number;
    }>;
    order_history: OrderRecord[];
    analysis?: {
      summary: string;
      key_interests: string[];
      pain_points: string[];
      recommended_action: string;
    };
  };
  messages: ChatMessage[];
  sentimentScore: number;
  dominantIntent: string;
}

export interface OrderRecord {
  order_id: string;
  purchase_date: string;
  amount: number;
  status: string;
  items: string[];
}

export interface ChatMessage {
  id: string;
  user_nick: string;
  sender_nick: string;
  msg_time: string;
  msg_type: string;
  content: string;
}

export interface DashboardMetrics {
  total_buyers: number;
  total_ltv: number;
  total_orders: number;
  total_chats: number;
  avg_ltv: number;
  vip_distribution: {
    'Non-VIP': number;
    'V0': number;
    'V1': number;
    'V2': number;
    'V3': number;
  };
}

export interface DailyStat {
  date: string;
  total_chats: number;
  avg_response_time: number;
  sentiment_score: number;
}

export interface ActionableCustomer {
  id: string;
  user_nick: string;
  issue_type: string;
  last_active: string;
  priority: string;
  status: string;
  action_suggestion: string;
}

// API Client Class
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || 'API request failed');
    }

    return response.json();
  }

  // Get list of buyers
  async getBuyers(params?: {
    limit?: number;
    offset?: number;
    start_date?: string;
    end_date?: string;
    search?: string;
  }): Promise<BuyerListResponse> {
    const queryParams = new URLSearchParams();
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.offset) queryParams.append('offset', params.offset.toString());
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);
    if (params?.search) queryParams.append('search', params.search);

    const queryString = queryParams.toString();
    return this.request<BuyerListResponse>(`/buyers${queryString ? `?${queryString}` : ''}`);
  }

  // Get complete buyer profile
  async getBuyerProfile(userNick: string, includeAi: boolean = false): Promise<BuyerProfile> {
    return this.request<BuyerProfile>(`/buyers/${encodeURIComponent(userNick)}?include_ai=${includeAi}`);
  }

  // Get buyer order history
  async getBuyerOrders(userNick: string, limit: number = 50): Promise<OrderRecord[]> {
    return this.request<OrderRecord[]>(`/buyers/${encodeURIComponent(userNick)}/orders?limit=${limit}`);
  }

  // Get buyer chat messages
  async getBuyerChats(userNick: string, limit: number = 100): Promise<ChatMessage[]> {
    return this.request<ChatMessage[]>(`/buyers/${encodeURIComponent(userNick)}/chats?limit=${limit}`);
  }

  // Trigger AI analysis for a buyer
  async analyzeBuyerWithAI(userNick: string): Promise<BuyerProfile> {
    return this.request<BuyerProfile>(`/buyers/${encodeURIComponent(userNick)}/ai-analysis`, {
      method: 'POST',
    });
  }

  // Get dashboard metrics
  async getDashboardMetrics(): Promise<DashboardMetrics> {
    return this.request<DashboardMetrics>('/dashboard/metrics');
  }

  // Get daily statistics
  async getDailyStats(days: number = 30): Promise<DailyStat[]> {
    return this.request<DailyStat[]>(`/dashboard/daily-stats?days=${days}`);
  }

  // Get actionable customers
  async getActionableCustomers(): Promise<ActionableCustomer[]> {
    return this.request<ActionableCustomer[]>('/dashboard/actionable-customers');
  }
}

// Export singleton instance
export const api = new ApiClient();

// Export hook for React components
export function useApi() {
  return api;
}
