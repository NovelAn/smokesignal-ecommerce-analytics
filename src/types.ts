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
  date: string;
  amount: number;
  status: 'Completed' | 'Shipped' | 'Refunded' | 'Pending';
  items: string[];
}

export interface CustomerProfile {
  user_nick: string;
  avatar_color: string;
  
  // Demographics
  city: string;
  is_new_customer: boolean; // New vs Old
  
  // Lifetime Data
  historical_ltv: number;       // Total spend
  total_orders: number;         // Frequency
  
  // Discount Analysis
  discount_spend_amount: number; 
  discount_ratio: number;       // (Discount Spend / Total Spend) * 100. Helps identify "Discount Seekers"
  
  // Recent Activity (L6M - Last 6 Months)
  l6m_spend: number;
  l6m_frequency: number;
  
  // Engagement
  recent_chat_frequency: number; // e.g., interactions in last 30 days
  avg_reply_interval_days: number; // Average days between sessions
  last_interaction_date: string;
  tags: string[];

  // Individual Intent Distribution (Radar Chart Data)
  intent_scores: { subject: IntentType; A: number; fullMark: number }[];

  // Purchase History
  order_history: OrderRecord[];

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