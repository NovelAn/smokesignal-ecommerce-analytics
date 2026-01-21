/**
 * Time range configurations for charts and filters
 */

export type TimeRange = '7d' | '15d' | '30d' | '90d' | '1y';

export const TIME_RANGE_LABELS: Record<TimeRange, string> = {
  '7d': '7 Days',
  '15d': '15 Days',
  '30d': '1 Mo',
  '90d': '1 Qtr',
  '1y': '1 Yr',
};

// Multipliers for data scaling based on time range
export const TIME_RANGE_MULTIPLIERS: Record<TimeRange, number> = {
  '7d': 0.1,
  '15d': 0.2,
  '30d': 0.35,
  '90d': 0.6,
  '1y': 1.0,
};
