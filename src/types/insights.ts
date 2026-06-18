export interface KeywordItem {
  keyword: string;
  count: number;
  percentage: number;
  examples?: string[];
}

export interface MotivationItem {
  pattern: string;
  count: number;
}

export interface VicPersona {
  total_vic_count: number;
  key_interests: KeywordItem[];
  key_pain_points: KeywordItem[];
  purchase_motivations: MotivationItem[];
  summary: {
    headline: string;
    bullets: string[];
  };
  raw_label_count: number;
  aggregated_theme_count: number;
}

export interface PeriodMetric {
  current: number;
  previous: number;
  change: number;
  change_pct: number | null;
}

export interface PeriodComparison {
  current_period: { start_date: string; end_date: string };
  comparison_period: { start_date: string; end_date: string };
  metrics: {
    new_vic: PeriodMetric;
    churn_warning: PeriodMetric;
    vip_upgrades: PeriodMetric;
    sentiment_negative: PeriodMetric;
  };
}

export interface VicPoolTrendPoint {
  month: string;
  SMOKER: number;
  VIC: number;
  BOTH: number;
}

export interface ActiveRateTrendPoint {
  month: string;
  total_vic: number;
  active_vic: number;
  active_rate: number;
}

export interface HighRiskTrendPoint {
  month: string;
  high_risk_count: number;
}

export interface SentimentTrendPoint {
  month: string;
  Positive: number;
  Neutral: number;
  Negative: number;
}

export interface CustomerTrends {
  vic_pool_trend: VicPoolTrendPoint[];
  vic_active_rate_trend: ActiveRateTrendPoint[];
  high_risk_trend: HighRiskTrendPoint[];
  sentiment_trend: SentimentTrendPoint[];
}

export type InventoryDetectionSource = 'ai' | 'keyword' | 'both';

export interface InventoryInquiry {
  buyer_nick: string;
  vip_level: string;
  inventory_questions: string[];
  question_count: number;
  last_inventory_msg_time: string | null;
  last_chat_date: string | null;
  dominant_intent: string;
  intent_distribution: Record<string, number>;
  sentiment_label: 'Neutral' | 'Positive' | 'Negative' | 'Unknown' | string;
  detected_by: InventoryDetectionSource;
  service_status: 'pending' | 'contacted' | 'resolved';
  service_notes: string;
  service_updated_at: string | null;
}

export interface InventoryInquiries {
  inquiries: InventoryInquiry[];
  total_count: number;
}

export type TimeRangePreset = '7D' | '15D' | '1M' | '1Q' | '1Y' | 'custom';

export interface TimeRange {
  start_date: string;
  end_date: string;
  preset: TimeRangePreset;
  /** 自定义对比期（可选，留空则后端自动算等长前期） */
  comparison_start_date?: string | null;
  comparison_end_date?: string | null;
}
