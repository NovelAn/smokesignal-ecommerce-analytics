/**
 * Unified color definitions for the application
 */

// Category colors from constants.ts
export const CATEGORY_COLORS: Record<string, string> = {
  Shipping: '#3B82F6',
  Specs: '#F59E0B',
  AfterSales: '#EF4444',
  Discount: '#10B981',
  Gifted: '#8B5CF6',
  Packaging: '#EC4899',
};

// Chart palette from App.tsx
export const CHART_PALETTE = [
  '#3B82F6', // Blue 500
  '#0EA5E9', // Sky 500
  '#06B6D4', // Cyan 500
  '#6366F1', // Indigo 500
  '#64748B', // Slate 500
  '#8B5CF6', // Violet 500
] as const;

// Cool tone palette for charts
export const COOL_PALETTE = [
  '#3B82F6', // Blue 500 (Primary)
  '#0EA5E9', // Sky 500
  '#06B6D4', // Cyan 500
  '#6366F1', // Indigo 500
  '#64748B', // Slate 500 (Neutral Cool)
  '#8B5CF6', // Violet 500 (Accent)
] as const;

export type ChartColor = typeof CHART_PALETTE[number];
