export enum IntentType {
  PRE_SALE = 'Pre-sale Inquiry',
  POST_SALE = 'Post-sale Support',
  LOGISTICS = 'Logistics',
  USAGE_GUIDE = 'Usage Guide',
  COMPLAINT = 'Complaint',
}

export enum SentimentType {
  POSITIVE = 'Positive',
  NEUTRAL = 'Neutral',
  NEGATIVE = 'Negative',
}

// Matches the DB Screenshot columns
export interface ChatMessage {
  id: string;
  user_nick: string;    // Buyer
  sender_nick: string;  // Seller (e.g., dunhill..., 崔华伟1984)
  msg_time: string;
  msg_type: 'text' | 'image' | 'system';
  content: string;
}

export interface CustomerAnalysis {
  summary: string;           // AI summary of interaction style and content
  key_interests: string[];   // What they care about (Price, Quality, etc.)
  pain_points: string[];     // Reported issues
  recommended_action: string; // Sales suggestion
}

export interface OrderRecord {
  order_id: string;
  sub_order_id?: string;
  date: string;
  gmv: number;              // 成交总金额
  gross_qty?: number;       // 总件数
  netsales: number;         // 净销售 = GMV - 退款
  net_qty?: number;         // 净件数 = 总件数 - 退款件数
  refund_amount: number;    // 退款金额
  refund_type?: string;     // 退款类型：仅退款/退货退款
  fp_md: string;           // FP/MD标识
  image_url?: string;      // 商品图片URL
  items: string[];         // 商品名称列表
  quantity?: number;       // 件数（兼容旧字段）
  refunded_qty?: number;   // 退款件数（内部计算）
}

export interface CustomerProfile {
  user_nick: string;
  avatar_color: string;

  // Demographics
  city: string;
  is_new_customer: boolean; // Deprecated: use client_monthly_tag
  client_monthly_tag?: string; // Directly from DB: 'new' or 'old'

  // Lifetime Data
  historical_ltv: number;       // Total spend
  historical_gmv?: number;      // Gross merchandise volume
  historical_refund?: number;   // Total refund amount
  historical_net_sales?: number; // Net sales
  refund_rate?: number;         // Refund rate percentage
  total_orders: number;         // Frequency

  // Discount Analysis
  discount_spend_amount: number;
  discount_ratio: number;       // (Discount Spend / Total Spend) * 100. Helps identify "Discount Seekers"

  // Recent Activity (L6M - Last 6 Months)
  l6m_spend: number;
  l6m_frequency: number;
  l6m_netsales?: number;
  l6m_orders?: number;
  l6m_gmv?: number;
  l6m_refund_rate?: number;

  // Last 1 Year Activity
  l1y_netsales?: number;
  l1y_orders?: number;
  l1y_gmv?: number;
  l1y_refund_rate?: number;

  // Engagement
  recent_chat_frequency: number; // e.g., interactions in last 30 days
  avg_reply_interval_days: number; // Average days between sessions
  last_interaction_date: string;
  last_chat_date?: string;
  tags: string[];

  // Individual Intent Distribution (Radar Chart Data)
  intent_scores: { subject: IntentType; A: number; fullMark: number }[];

  // Purchase History
  order_history: OrderRecord[];
  chat_history?: ChatMessage[];

  // AI Content Analysis
  analysis: CustomerAnalysis;
}

export interface BuyerSession {
  user_nick: string;
  messages: ChatMessage[];
  profile: CustomerProfile; // Linked profile data
  sentimentScore: number;
  dominantIntent: IntentType;
}

export interface KeywordMetric {
  text: string;
  value: number; // Frequency
  category: 'Shipping' | 'Specs' | 'After-sales' | 'Discount' | 'Gifted' | 'Packaging';
  x?: number; // For visualization positioning
  y?: number; // For visualization positioning
  fill?: string; // For visualization color
}

export interface DailyStat {
  date: string;
  totalChats: number;
  avgResponseTime: number;
  sentimentScore: number;
}

export interface ActionableCustomer {
  id: string;
  user_nick: string;
  issue_type: 'Churn Risk' | 'Negative Review' | 'Stockout Request' | 'Gift Inquiry' | 'High Value';
  last_active: string;
  priority: 'High' | 'Medium' | 'Low';
  status: 'Pending' | 'Followed Up' | 'Resolved';
  action_suggestion: string;
}

// ============================================
// External Records Types (场外信息)
// ============================================

/**
 * 场外信息记录类型
 */
export type ExternalRecordType = 'communication' | 'purchase';

/**
 * 场外信息记录接口
 * 用于存储客户的线下消费和私域沟通记录
 */
export interface ExternalRecord {
  id: string;
  user_nick: string;
  record_type: ExternalRecordType;
  record_date: string;
  channel: string | null;      // 微信/电话/门店名称
  content: string | null;      // 内容描述
  notes: string | null;        // 备注
  amount: number | null;       // 消费金额（仅消费类型）
  category: string | null;     // 商品品类（仅消费类型）
  created_by: string | null;   // 录入人
  created_at: string;
  updated_at: string;
}

/**
 * 场外信息列表响应
 */
export interface ExternalRecordsListResponse {
  records: ExternalRecord[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * 场外信息统计
 */
export interface ExternalRecordsStats {
  total_records: number;
  communication_count: number;
  purchase_count: number;
  total_offline_amount: number;
  top_channels: Array<{ channel: string; count: number }>;
  recent_records: ExternalRecord[];
}

/**
 * 批量导入结果
 */
export interface BatchImportResult {
  success_count: number;
  failed_count: number;
  errors: string[];
  parse_errors?: string[];
}