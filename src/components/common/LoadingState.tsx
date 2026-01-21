import React from 'react';
import { Loader2 } from 'lucide-react';

/**
 * 加载状态组件
 */
export const LoadingSpinner: React.FC<{ size?: number; text?: string }> = ({
  size = 24,
  text
}) => (
  <div className="flex flex-col items-center justify-center p-8 space-y-3">
    <Loader2 className="text-notion-muted animate-spin" size={size} />
    {text && <p className="text-sm text-notion-muted">{text}</p>}
  </div>
);

/**
 * 卡片骨架屏（加载时显示）
 */
export const CardSkeleton: React.FC = () => (
  <div className="bg-notion-bg border border-notion-border rounded-sm shadow-card p-4 animate-pulse">
    <div className="h-4 bg-notion-gray_bg rounded w-1/3 mb-4"></div>
    <div className="h-8 bg-notion-gray_bg rounded w-1/2 mb-2"></div>
    <div className="h-3 bg-notion-gray_bg rounded w-1/4"></div>
  </div>
);

/**
 * 表格骨架屏
 */
export const TableSkeleton: React.FC<{ rows?: number }> = ({ rows = 5 }) => (
  <div className="space-y-3">
    {Array.from({ length: rows }).map((_, i) => (
      <div key={i} className="flex items-center space-x-4 p-3 border border-notion-border rounded animate-pulse">
        <div className="flex-1 space-y-2">
          <div className="h-4 bg-notion-gray_bg rounded w-1/4"></div>
          <div className="h-3 bg-notion-gray_bg rounded w-1/6"></div>
        </div>
        <div className="h-4 bg-notion-gray_bg rounded w-1/6"></div>
        <div className="h-4 bg-notion-gray_bg rounded w-1/8"></div>
      </div>
    ))}
  </div>
);

/**
 * 指标卡片骨架屏
 */
export const MetricCardSkeleton: React.FC = () => (
  <div className="bg-notion-bg border border-notion-border rounded-sm shadow-card p-4 animate-pulse">
    <div className="h-3 bg-notion-gray_bg rounded w-1/2 mb-2"></div>
    <div className="h-8 bg-notion-gray_bg rounded w-1/3 mb-2"></div>
    <div className="h-3 bg-notion-gray_bg rounded w-1/5"></div>
  </div>
);
