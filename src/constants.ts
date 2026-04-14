import { BuyerSession, IntentType, KeywordMetric, DailyStat, SentimentType, CustomerProfile, ChatMessage, ActionableCustomer } from './types';

const getDate = (daysAgo: number) => {
  const date = new Date();
  date.setDate(date.getDate() - daysAgo);
  return date.toISOString().split('T')[0];
};

// Colors for categories
const COLORS = {
  Shipping: '#3B82F6',   // Blue
  Specs: '#F59E0B',      // Orange
  AfterSales: '#EF4444', // Red
  Discount: '#10B981',   // Green
  Gifted: '#8B5CF6',     // Purple
  Packaging: '#EC4899'   // Pink
};

// Data with manually distributed X (category groups) and random Y for bubble cloud effect
export const KEYWORD_DATA: KeywordMetric[] = [
  // Specs (Product Attributes) - X range ~ 10-30
  { text: 'Borosilicate', value: 150, category: 'Specs', x: 15, y: 50, fill: COLORS.Specs },
  { text: 'Dimensions', value: 120, category: 'Specs', x: 25, y: 70, fill: COLORS.Specs },
  { text: 'Curved Pipe', value: 90, category: 'Specs', x: 10, y: 30, fill: COLORS.Specs },
  { text: 'Heat Resist', value: 80, category: 'Specs', x: 28, y: 20, fill: COLORS.Specs },
  { text: 'Cleaning', value: 75, category: 'Specs', x: 20, y: 85, fill: COLORS.Specs },

  // Shipping (Logistics) - X range ~ 40-60
  { text: 'SF Express', value: 130, category: 'Shipping', x: 45, y: 60, fill: COLORS.Shipping },
  { text: 'Ship Today?', value: 110, category: 'Shipping', x: 55, y: 40, fill: COLORS.Shipping },
  { text: 'Tracking', value: 60, category: 'Shipping', x: 42, y: 20, fill: COLORS.Shipping },
  { text: 'Where from?', value: 50, category: 'Shipping', x: 58, y: 80, fill: COLORS.Shipping },

  // Discount - X range ~ 70-90
  { text: 'Cheaper?', value: 140, category: 'Discount', x: 75, y: 50, fill: COLORS.Discount },
  { text: 'Coupon', value: 95, category: 'Discount', x: 85, y: 75, fill: COLORS.Discount },
  { text: 'Sale?', value: 60, category: 'Discount', x: 72, y: 25, fill: COLORS.Discount },

  // After-sales - X range ~ 100-120
  { text: 'Broken', value: 85, category: 'After-sales', x: 105, y: 65, fill: COLORS.AfterSales },
  { text: 'Refund', value: 40, category: 'After-sales', x: 115, y: 35, fill: COLORS.AfterSales },

  // Packaging - X range ~ 130-140
  { text: 'Discrete?', value: 70, category: 'Packaging', x: 130, y: 55, fill: COLORS.Packaging },
  { text: 'Gift Bag', value: 45, category: 'Packaging', x: 140, y: 40, fill: COLORS.Packaging },
  
  // Gifted - X range ~ 150
  { text: 'Freebie?', value: 55, category: 'Gifted', x: 150, y: 60, fill: COLORS.Gifted },
];

export const DAILY_STATS: DailyStat[] = Array.from({ length: 7 }).map((_, i) => ({
  date: getDate(6 - i),
  totalChats: Math.floor(Math.random() * 200) + 100,
  avgResponseTime: Math.floor(Math.random() * 5) + 1,
  sentimentScore: 0.2 + Math.random() * 0.6, 
}));

export const INTENT_DISTRIBUTION = [
  { subject: IntentType.PRE_SALE, A: 120, fullMark: 150 },
  { subject: IntentType.POST_SALE, A: 98, fullMark: 150 },
  { subject: IntentType.LOGISTICS, A: 86, fullMark: 150 },
  { subject: IntentType.USAGE_GUIDE, A: 99, fullMark: 150 },
  { subject: IntentType.COMPLAINT, A: 35, fullMark: 150 },
];

export const HOURLY_ACTIVITY = [
  { hour: '00:00', value: 10 }, { hour: '02:00', value: 5 },
  { hour: '04:00', value: 2 }, { hour: '06:00', value: 8 },
  { hour: '08:00', value: 40 }, { hour: '10:00', value: 120 },
  { hour: '12:00', value: 150 }, { hour: '14:00', value: 130 },
  { hour: '16:00', value: 110 }, { hour: '18:00', value: 90 },
  { hour: '20:00', value: 160 }, { hour: '22:00', value: 80 },
];

export const ACTIONABLE_CUSTOMERS: ActionableCustomer[] = [
  { id: '1', user_nick: 'SmokeMaster_SH', issue_type: 'Churn Risk', last_active: '2 Days ago', priority: 'High', status: 'Pending', action_suggestion: 'Send re-engagement coupon' },
  { id: '2', user_nick: 'PipeDream_007', issue_type: 'Negative Review', last_active: '1 Hour ago', priority: 'High', status: 'Pending', action_suggestion: 'Apologize & Offer Refund' },
  { id: '3', user_nick: 'RetroVibe_X', issue_type: 'Stockout Request', last_active: '4 Hours ago', priority: 'Medium', status: 'Followed Up', action_suggestion: 'Notify when stock arrives' },
  { id: '4', user_nick: 'Collector_99', issue_type: 'High Value', last_active: '1 Day ago', priority: 'Medium', status: 'Resolved', action_suggestion: 'VIP Personal Service' },
  { id: '5', user_nick: 'Newbie_Cloud', issue_type: 'Gift Inquiry', last_active: '30 Mins ago', priority: 'Low', status: 'Pending', action_suggestion: 'Recommend Gift Set' },
];

// --- MOCK CUSTOMERS BASED ON SCREENSHOT CONTEXT ---

const USER_1 = '崔华伟1984'; // The main user from screenshot
const USER_2 = 'SmokeMaster_SH';
const USER_3 = 'NewBuyer_BJ';

const PROFILE_1: CustomerProfile = {
  user_nick: USER_1,
  avatar_color: 'bg-orange-200 text-orange-800',
  city: 'Shanghai',
  is_new_customer: false,
  historical_ltv: 12500.50,
  total_orders: 12,
  discount_spend_amount: 8500.00,
  discount_ratio: 68, // High discount sensitivity
  l6m_spend: 3200.00,
  l6m_frequency: 3,
  recent_chat_frequency: 15,
  avg_reply_interval_days: 2.5,
  last_interaction_date: '2026-01-10',
  tags: ['VIP', 'Discount Seeker', 'Pipe Enthusiast'],
  intent_scores: [
    { subject: IntentType.PRE_SALE, A: 140, fullMark: 150 },
    { subject: IntentType.POST_SALE, A: 40, fullMark: 150 },
    { subject: IntentType.LOGISTICS, A: 20, fullMark: 150 },
    { subject: IntentType.USAGE_GUIDE, A: 80, fullMark: 150 },
    { subject: IntentType.COMPLAINT, A: 10, fullMark: 150 },
  ],
  order_history: [
    { order_id: 'ORD-20260115', date: '2026-01-15', gmv: 1200.00, netsales: 1200.00, refund_amount: 0, fp_md: 'FP', items: ['Hand-Carved Briar Pipe', 'Filter Pack x50'] },
    { order_id: 'ORD-20251120', date: '2025-11-20', gmv: 850.50, netsales: 850.50, refund_amount: 0, fp_md: 'FP', items: ['Borosilicate Glass Stem', 'Cleaning Kit'] },
    { order_id: 'ORD-20250910', date: '2025-09-10', gmv: 10450.00, netsales: 10450.00, refund_amount: 0, fp_md: 'FP', items: ['Limited Edition Meerschaum Set', 'Premium Stand'] },
    { order_id: 'ORD-20250601', date: '2025-06-01', gmv: 450.00, netsales: 450.00, refund_amount: 0, fp_md: 'FP', items: ['Beginner Pipe Kit'] }
  ],
  analysis: {
    summary: "Experienced buyer with specific product knowledge. Frequently negotiates for stock that is offline/sold out. Shows high price sensitivity but purchases high-ticket items when available.",
    key_interests: ["Product Availability", "Restocking", "Borosilicate Glass"],
    pain_points: ["Stock Outages", "Discontinued Items"],
    recommended_action: "Notify immediately when 'Curved Pipe' is back in stock. Offer pre-order for next limited batch."
  }
};

const PROFILE_2: CustomerProfile = {
  user_nick: USER_2,
  avatar_color: 'bg-blue-200 text-blue-800',
  city: 'Shenzhen',
  is_new_customer: false,
  historical_ltv: 450.00,
  total_orders: 2,
  discount_spend_amount: 0,
  discount_ratio: 0,
  l6m_spend: 0,
  l6m_frequency: 0,
  recent_chat_frequency: 2,
  avg_reply_interval_days: 14,
  last_interaction_date: '2026-01-08',
  tags: ['Churn Risk', 'Low Frequency'],
  intent_scores: [
    { subject: IntentType.PRE_SALE, A: 20, fullMark: 150 },
    { subject: IntentType.POST_SALE, A: 30, fullMark: 150 },
    { subject: IntentType.LOGISTICS, A: 150, fullMark: 150 },
    { subject: IntentType.USAGE_GUIDE, A: 10, fullMark: 150 },
    { subject: IntentType.COMPLAINT, A: 120, fullMark: 150 },
  ],
  order_history: [
    { order_id: 'ORD-20250210', date: '2025-02-10', gmv: 225.00, netsales: 225.00, refund_amount: 0, fp_md: 'FP', items: ['Standard Pipe - Black'] },
    { order_id: 'ORD-20250105', date: '2025-01-05', gmv: 225.00, netsales: 225.00, refund_amount: 0, fp_md: 'FP', items: ['Standard Pipe - Brown'] }
  ],
  analysis: {
    summary: "Transactional customer focused solely on delivery speed. Frustrated by lack of tracking updates. Low engagement with product features.",
    key_interests: ["Shipping Speed", "Tracking Info"],
    pain_points: ["Delivery Delay", "Logistics Visibility"],
    recommended_action: "Provide automated tracking link. Offer free shipping coupon for next order to re-engage."
  }
};

const PROFILE_3: CustomerProfile = {
  user_nick: USER_3,
  avatar_color: 'bg-green-200 text-green-800',
  city: 'Beijing',
  is_new_customer: true,
  historical_ltv: 0,
  total_orders: 0,
  discount_spend_amount: 0,
  discount_ratio: 0,
  l6m_spend: 0,
  l6m_frequency: 0,
  recent_chat_frequency: 8,
  avg_reply_interval_days: 1,
  last_interaction_date: '2026-01-09',
  tags: ['New Lead', 'High Intent'],
  intent_scores: [
    { subject: IntentType.PRE_SALE, A: 140, fullMark: 150 },
    { subject: IntentType.POST_SALE, A: 10, fullMark: 150 },
    { subject: IntentType.LOGISTICS, A: 30, fullMark: 150 },
    { subject: IntentType.USAGE_GUIDE, A: 120, fullMark: 150 },
    { subject: IntentType.COMPLAINT, A: 0, fullMark: 150 },
  ],
  order_history: [],
  analysis: {
    summary: "New entrant to the hobby. Asks educational questions about usage and maintenance. Seeking validation for 'Beginner Friendly' products.",
    key_interests: ["Usage Guide", "Cleaning", "Beginner Kits"],
    pain_points: ["Complexity of use", "Maintenance anxiety"],
    recommended_action: "Send 'Starter Guide PDF'. Recommend the 'Easy-Clean' series pipes."
  }
};

export const MOCK_SESSIONS: BuyerSession[] = [
  {
    user_nick: USER_1,
    profile: PROFILE_1,
    sentimentScore: 0.8,
    dominantIntent: IntentType.PRE_SALE,
    messages: [
      { id: '818', user_nick: USER_1, sender_nick: 'dunhill官方旗舰店:lei', msg_time: '2026-01-07 12:38:04', msg_type: 'text', content: '好哒' },
      { id: '819', user_nick: USER_1, sender_nick: 'dunhill官方旗舰店:lei', msg_time: '2026-01-07 12:38:13', msg_type: 'text', content: '您需要2支' },
      { id: '820', user_nick: USER_1, sender_nick: 'dunhill官方旗舰店:lei', msg_time: '2026-01-07 12:38:24', msg_type: 'text', content: '还是1支呢' },
      { id: '822', user_nick: USER_1, sender_nick: USER_1, msg_time: '2026-01-07 12:38:36', msg_type: 'text', content: '其实我想要这个' },
      { id: '823', user_nick: USER_1, sender_nick: USER_1, msg_time: '2026-01-07 12:38:45', msg_type: 'text', content: '看看能调到货不' },
      { id: '824', user_nick: USER_1, sender_nick: USER_1, msg_time: '2026-01-07 12:39:04', msg_type: 'text', content: '这个你们店里为什么下架' },
      { id: '826', user_nick: USER_1, sender_nick: USER_1, msg_time: '2026-01-07 12:39:14', msg_type: 'text', content: '我给您反馈问下' },
      { id: '852', user_nick: USER_1, sender_nick: USER_1, msg_time: '2026-01-10 21:02:18', msg_type: 'text', content: '我第一次抽，给我讲讲' },
    ]
  },
  {
    user_nick: USER_2,
    profile: PROFILE_2,
    sentimentScore: 0.1,
    dominantIntent: IntentType.LOGISTICS,
    messages: [
       { id: '101', user_nick: USER_2, sender_nick: USER_2, msg_time: '2026-01-08 14:00:00', msg_type: 'text', content: '我的快递到哪里了？' },
       { id: '102', user_nick: USER_2, sender_nick: 'dunhill官方旗舰店:hao', msg_time: '2026-01-08 14:05:00', msg_type: 'text', content: '亲，这边帮您查询一下，请稍等。' },
    ]
  },
  {
    user_nick: USER_3,
    profile: PROFILE_3,
    sentimentScore: 0.6,
    dominantIntent: IntentType.PRE_SALE,
    messages: [
       { id: '201', user_nick: USER_3, sender_nick: USER_3, msg_time: '2026-01-09 09:30:00', msg_type: 'text', content: '这款斗适合新手吗？' },
       { id: '202', user_nick: USER_3, sender_nick: 'dunhill官方旗舰店:lei', msg_time: '2026-01-09 09:32:00', msg_type: 'text', content: '非常适合，这是我们针对入门级玩家设计的经典款。' },
    ]
  }
];