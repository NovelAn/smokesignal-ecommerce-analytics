export type V2Sentiment = 'Positive' | 'Neutral' | 'Negative' | 'Unknown';
export type AttentionPriority = 'urgent' | 'high' | 'medium' | 'low';
export type IssueSeverity = 'low' | 'medium' | 'high' | 'critical';
export type IssueStatus = 'open' | 'explained_pending_acceptance' | 'resolved' | 'unknown';

export interface V2Issue {
  id: number;
  event_id: number;
  issue_category: string;
  issue_code: string;
  issue_detail: string;
  severity: IssueSeverity;
  owner: 'product' | 'logistics' | 'service' | 'customer' | 'mixed' | 'unknown';
  status: IssueStatus;
  is_primary: boolean;
  evidence_text: string;
  evidence_msg_time: string | null;
}

export interface V2Event {
  id: number;
  topic_summary: string;
  event_started_at: string;
  event_ended_at: string;
  sentiment_label: Exclude<V2Sentiment, 'Unknown'>;
  sentiment_score: number;
  sentiment_basis: string;
  peak_emotion: string;
  service_friction: 'none' | 'low' | 'medium' | 'high';
  resolution_status: 'unresolved' | 'explained_pending_acceptance' | 'resolved' | 'unknown';
  customer_accepted: boolean | null;
  suggested_action: string;
  issues: V2Issue[];
}

export interface V2CustomerState {
  buyer_nick: string;
  current_sentiment_label: V2Sentiment;
  primary_issue_code: string | null;
  primary_issue_detail: string | null;
  active_issue_count: number;
  highest_severity: IssueSeverity | null;
  attention_priority: AttentionPriority;
  recommended_action: string;
  analyzed_through_msg_time: string | null;
  last_event_at: string | null;
  last_run_id: number;
}

export interface V2BuyerAnalysis {
  customer_state: V2CustomerState | null;
  events: V2Event[];
  issues: V2Issue[];
}

export interface V2AnalysisRunResult extends V2BuyerAnalysis {
  status: 'completed' | 'skipped';
  provider: 'minimax' | 'deepseek' | 'cache';
  reason: string | null;
}
