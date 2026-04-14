import type { ComponentType } from 'react';

export interface MetricCard {
  label: string;
  value: string;
  change: string;
  icon: ComponentType<{ size?: number }>;
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
